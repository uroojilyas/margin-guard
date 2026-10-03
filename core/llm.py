import os, json
from dotenv import load_dotenv
from groq import Groq
from core.tools import simulate_cost_increase
import re

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-120b"   # console.groq.com par current model check karo

SYSTEM = """You extract products from a supplier price list written in messy
Arabic/English (WhatsApp style). Return ONLY a JSON object:
{"items": [{"name": "<product name as written>", "new_cost": <number in EGP>}]}
Rules: convert Arabic digits to normal digits. Ignore greetings and non-product text.
Do not invent items. If a price is unclear, skip the item."""

def parse_supplier_list(text: str):
    r = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(r.choices[0].message.content)["items"]

def resolve_match(supplier_name: str, candidates: list):
    """candidates: [(id, name, name_ar), ...]. Returns product id or None."""
    options = "\n".join(f"{c[0]}: {c[1]} / {c[2]}" for c in candidates)
    prompt = f"""Supplier item: "{supplier_name}"
Shop products:
{options}

Which shop product is the SAME item (same model, same capacity/size)?
Return ONLY JSON: {{"product_id": <id or null>}}.
If unsure or capacity/size differs, return null."""
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(r.choices[0].message.content).get("product_id")

def generate_message(changes: list):
    """changes: [{"product": str, "old_price": number, "new_price": number}, ...]"""
    lines = "\n".join(
        f"- {c['product']}: {c['old_price']:.0f} EGP -> {c['new_price']:.0f} EGP"
        for c in changes
    )
    prompt = f"""Write a short, polite WhatsApp announcement from a mobile accessories shop
to its customers about updated prices. Use ONLY these items and numbers:
{lines}

Write it twice: first in English, then in friendly Egyptian Arabic dialect.
Separate the two with a line containing only ---.
Do not mention discounts, offers, or reasons that are not given. Keep each version under 120 words."""
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    return r.choices[0].message.content

TOOLS = [{
    "type": "function",
    "function": {
        "name": "simulate_cost_increase",
        "description": "Simulate a supplier/dollar cost increase of X percent on ALL shop products "
                       "and list which items would sell at a loss or below the minimum margin.",
        "parameters": {
            "type": "object",
            "properties": {
                "percent": {"type": "number",
                            "description": "Cost increase in percent, e.g. 5 for +5%"}
            },
            "required": ["percent"],
        },
    },
}]

AGENT_SYSTEM = """You are Margin Guard, an assistant for a small mobile accessories shop owner in Egypt.
You can ONLY answer what-if questions about supplier or dollar cost increases.
For those, you MUST call the tool simulate_cost_increase with the percentage given.
Then explain the result using ONLY numbers returned by the tool. Never invent numbers.
Always answer in English. All money is in EGP (Egyptian pounds), never rupees or dollars.
Always mention: total items at risk, how many are newly at risk, how many are losing money,
and the monthly profit erosion total. Then list the top 3 items. For each item, show: cost_after_increase, current_price (label it "current price"),
and suggested_price (label it "suggested price"). Never call suggested_price just "price".Keep it short."""

HELP_MESSAGE = """I can answer **what-if questions about cost or dollar increases**. Try:

- If the dollar rises 5%, which items start losing money?
- What happens to my margins if costs rise 10%?
- How much profit would I lose if supplier prices go up 15%?

Please include a percentage in your question."""


def ask_agent(question: str, min_margin: float = 0.15):
    """Returns (answer_text, tool_calls). Off-topic questions get a fixed help message."""
    # no number in the question -> not a what-if question, no need to call the model
    if not re.search(r"\d", question):
        return HELP_MESSAGE, []

    messages = [
        {"role": "system", "content": AGENT_SYSTEM},
        {"role": "user", "content": question},
    ]
    r = client.chat.completions.create(
        model=MODEL, messages=messages, tools=TOOLS, tool_choice="auto", temperature=0
    )
    msg = r.choices[0].message
    if not msg.tool_calls:
        return HELP_MESSAGE, []

    messages.append({
        "role": "assistant",
        "content": msg.content or "",
        "tool_calls": [
            {"id": tc.id, "type": "function",
             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ],
    })

    calls = []
    for tc in msg.tool_calls:
        args = json.loads(tc.function.arguments or "{}")
        percent = float(args.get("percent", 0))
        if not 0 < percent <= 100:
            return "Please give a cost increase between 0% and 100%.", []
        result = simulate_cost_increase(percent, min_margin)
        calls.append((tc.function.name, args, result))
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})

    r2 = client.chat.completions.create(model=MODEL, messages=messages, temperature=0.2)
    return r2.choices[0].message.content, calls