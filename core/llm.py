import os, json
from dotenv import load_dotenv
from groq import Groq

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