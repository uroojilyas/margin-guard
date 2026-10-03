import json
from core.llm import client, MODEL, parse_supplier_list
from core.matcher import load_products, match_items
from core.margins import build_report, summary
from core.tools import simulate_cost_increase

MAX_STEPS = 8

SYSTEM = """You are Margin Guard, an agent for an Egyptian mobile accessories shop owner.
The owner gives you a request, and may have loaded a supplier price list.
You have tools. Decide yourself which tools are needed, and call them one at a time, using each result
to choose the next step. Call ONLY the tools the request needs.
- To analyze a supplier list: parse_supplier_list, then match_products, then compute_margins.
  If compute_margins shows any LOSS or LOW item, also call simulate_cost_increase with percent 5.
- For what-if questions about cost or dollar increases, call simulate_cost_increase with the percent
  the owner gave. This does not need a supplier list.
- If no supplier list is loaded and the request needs one, say so and ask the owner to paste it.
Rules:
- Use ONLY numbers returned by tools. Never invent numbers. All money is in EGP. Answer in English.
- Label current_price as "current price" and suggested_price as "suggested price".
- For needs_owner_confirmation, name items using matched_to_shop_product. Never translate supplier text.
- For what-if results, name EVERY product in already_at_risk_products and newly_at_risk_products
  and state the counts. Never work this out yourself.
- If the owner asks about specific products only, report only those.
- You can NOT change prices: the owner approves changes in the Review & approve tab.
- If the request is not about margins, prices, costs or supplier lists, briefly say what you can do.
Keep the answer short and structured: what you found, what needs action, a warning if relevant,
and the next step."""

TOOLS = [
    {"type": "function", "function": {
        "name": "parse_supplier_list",
        "description": "Read the supplier's pasted price list and extract product names with new costs.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "match_products",
        "description": "Match the parsed supplier items to the shop's own products. "
                       "Call after parse_supplier_list.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "compute_margins",
        "description": "Compute margins on the new costs, flag LOSS/LOW items and suggest new prices. "
                       "Call after match_products.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "simulate_cost_increase",
        "description": "What-if: apply a further cost increase of X percent on the shop's CURRENT costs "
                       "and list which items would lose money or fall below the minimum margin.",
        "parameters": {"type": "object",
                       "properties": {"percent": {"type": "number", "description": "e.g. 5 for +5%"}},
                       "required": ["percent"]}}},
]


def _parse(state, args):
    if not state["text"].strip():
        return {"error": "No supplier list was provided."}
    items = parse_supplier_list(state["text"])
    state["parsed"] = items
    return {"items_found": len(items), "items": items}


def _match(state, args):
    if not state.get("parsed"):
        return {"error": "Call parse_supplier_list first."}
    matches = match_items(state["parsed"], load_products())
    state["matches"] = matches
    return {
        "matched_automatically": sum(m["status"] == "auto" for m in matches),
        "needs_owner_confirmation": [
            {"supplier_wrote": m["supplier_name"], "matched_to_shop_product": m["product_name"]}
            for m in matches if m["status"] == "confirm"],
        "unmatched": [m["supplier_name"] for m in matches if m["product_id"] is None],
    }


def _margins(state, args):
    if not state.get("matches"):
        return {"error": "Call match_products first."}
    df = build_report(state["matches"], load_products(), state["min_margin"])
    state["df"] = df
    flagged = df[df["status"] != "OK"]
    cols = ["product", "status", "margin_after_pct", "current_price",
            "suggested_price", "profit_erosion_month"]
    return {"summary": summary(df), "flagged_items": flagged[cols].head(8).to_dict("records")}


def _whatif(state, args):
    percent = float(args.get("percent", 0))
    if not 0 < percent <= 100:
        return {"error": "percent must be between 0 and 100"}
    r = simulate_cost_increase(percent, state["min_margin"])
    r["newly_at_risk_products"] = [i["product"] for i in r["items"] if not i["already_at_risk_today"]]
    r["already_at_risk_products"] = [i["product"] for i in r["items"] if i["already_at_risk_today"]]
    # all items, but only the fields the model needs (keeps the result short)
    r["items"] = [
        {"product": i["product"], "current_price": i["current_price"],
         "suggested_price": i["suggested_price"], "margin_after_pct": i["margin_after_pct"],
         "status_after": i["status_after"]}
        for i in r["items"]
    ]
    return r


HANDLERS = {"parse_supplier_list": _parse, "match_products": _match,
            "compute_margins": _margins, "simulate_cost_increase": _whatif}


def run_agent(text: str, min_margin: float = 0.15, on_step=None, instruction: str = ""):
    """Returns {"answer": str, "steps": [{"tool","args","result"}], "state": dict}."""
    state = {"text": text or "", "min_margin": min_margin}
    steps = []
    has_list = "yes" if state["text"].strip() else "no"
    request = instruction.strip() or "Analyze the supplier list and tell me what needs my attention."
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Supplier list loaded: {has_list}.\nOwner request: {request}"},
    ]
    for _ in range(MAX_STEPS):
        r = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, tool_choice="auto", temperature=0)
        msg = r.choices[0].message
        if not msg.tool_calls:
            return {"answer": msg.content or "", "steps": steps, "state": state}

        messages.append({
            "role": "assistant", "content": msg.content or "",
            "tool_calls": [{"id": tc.id, "type": "function",
                            "function": {"name": tc.function.name,
                                         "arguments": tc.function.arguments}}
                           for tc in msg.tool_calls]})
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
                handler = HANDLERS.get(tc.function.name)
                result = handler(state, args) if handler else {"error": "Unknown tool"}
            except Exception as e:
                args, result = {}, {"error": str(e)}
            steps.append({"tool": tc.function.name, "args": args, "result": result})
            if on_step:
                on_step(steps[-1])
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": json.dumps(result, default=str)})

    return {"answer": "The agent reached its step limit. Please try again.",
            "steps": steps, "state": state}