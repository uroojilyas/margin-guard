import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from urllib.parse import quote

import ui
from core.llm import parse_supplier_list, generate_message
from core.matcher import load_products, match_items
from core.margins import build_report, summary
from core.db import apply_changes, replace_products
from data.seed import seed
from core.agent import run_agent
import os
if not os.path.exists("shop.db"):
    seed()

st.set_page_config(page_title="Margin Guard", page_icon="🛡️", layout="wide",
                   initial_sidebar_state="expanded")
ui.inject()

if "page" not in st.session_state:
    st.session_state.page = st.query_params.get("page", "landing")

# ======================= LANDING =======================
if st.session_state.page == "landing":
    ui.landing()
    _, mid, _ = st.columns([2, 1.2, 2])
    if mid.button("Get Started  →", type="primary", use_container_width=True):
        st.session_state.page = "app"
        st.query_params["page"] = "app"
        st.rerun()
    st.stop()

# ======================= APP =======================
top1, top2 = st.columns([6, 1])
top1.markdown("## 🛡️ Margin Guard")
if top2.button("← Home"):
    st.session_state.page = "landing"
    st.query_params["page"] = "landing"
    st.rerun()
st.caption("Demo with sample shop data. The owner approves every change.")

with st.sidebar:
    ui.sidebar_head()

    _prods = load_products()
    _avg = sum((p["price"] - p["cost"]) / p["price"] for p in _prods) / len(_prods) * 100
    _units = sum(p["monthly_units"] for p in _prods)
    ui.sidebar_shop(len(_prods), _avg, _units)

    st.markdown('<div class="sb-label">Target margin</div>', unsafe_allow_html=True)
    min_margin = st.slider(
        "Minimum margin %", 5, 40, 15, label_visibility="collapsed",
        help="Items earning less than this are flagged LOW. Negative margin means LOSS.",
    ) / 100
    st.caption(f"Flag items earning less than {min_margin*100:.0f}% profit.")

    st.markdown('<div class="sb-label">Demo</div>', unsafe_allow_html=True)
    if st.button("Reset sample shop", use_container_width=True):
        seed()
        for k in ("matches", "result"):
            st.session_state.pop(k, None)
        st.rerun()

    ui.sidebar_steps()


def load_sample():
    st.session_state.supplier_text = open(
        "data/supplier_sample.txt", encoding="utf-8"
    ).read()


tab4, tab1, tab2 = st.tabs(
    [" Agent mode", " Review & approve", " Shop inventory"]
)

# ---------- inventory tab ----------
with tab2:
    st.subheader("Shop inventory (current cost and selling price)")
    if st.session_state.get("inv_msg"):
        st.success(st.session_state.pop("inv_msg"))

    inv = pd.DataFrame(load_products())[["name", "name_ar", "cost", "price", "monthly_units"]]
    inv.columns = ["Product", "Arabic name (optional)", "Cost (EGP)",
                   "Selling price (EGP)", "Units sold / month"]
    st.dataframe(inv, hide_index=True, width="stretch")
    st.caption("The Arabic name is optional. It helps the agent match Arabic supplier lists "
               "to your products. Leave it empty if you don't have one.")

    st.markdown("#### Use your own shop data")
    st.caption("Upload a CSV with columns: name, name_ar (optional), cost, price, monthly_units. "
               "In Excel use Save As → CSV UTF-8.")
    template = "name,name_ar,cost,price,monthly_units\nSamsung 25W Charger,شاحن سامسونج 25W,350,420,40\n"
    st.download_button("⬇Download CSV template", template.encode("utf-8-sig"),
                       file_name="inventory_template.csv", mime="text/csv")
    up = st.file_uploader("Upload inventory CSV", type="csv", key="inv_upload")
    if up is not None:
        try:
            try:
                new_df = pd.read_csv(up, encoding="utf-8-sig")
            except UnicodeDecodeError:
                up.seek(0)
                new_df = pd.read_csv(up, encoding="cp1256")
            st.write("Preview:")
            st.dataframe(new_df.head(10), hide_index=True, width="stretch")
            if st.button("Use this inventory", type="primary", key="use_inv"):
                n = replace_products(new_df)
                for k in ("matches", "result"):
                    st.session_state.pop(k, None)
                st.session_state.inv_msg = f"Loaded {n} products from your file. Go to the Analyze tab."
                st.rerun()
        except Exception as e:
            st.error(f"Could not read the file: {e}")

# ---------- analyze tab ----------
with tab1:
    st.subheader("1. Paste supplier price list")
    st.caption("Quick mode: paste a list here for a direct analysis. "
               "Or run Agent mode first and send its result here for approval.")
    st.text_area("Supplier list", key="supplier_text", height=200,
                 placeholder="Paste the WhatsApp price list here...",
                 label_visibility="collapsed")
    c1, c2, _ = st.columns([1, 1, 5])
    c1.button("Load sample", on_click=load_sample)
    if c2.button("Analyze", type="primary"):
        text = st.session_state.get("supplier_text", "").strip()
        if not text:
            st.error("Paste a list first (or click Load sample).")
        else:
            try:
                with st.spinner("Reading the list and matching products..."):
                    parsed = parse_supplier_list(text)
                    st.session_state.matches = match_items(parsed, load_products())
                st.session_state.pop("result", None)
            except Exception:
                st.error("The AI service is busy or its free limit was reached. "
                         "Please wait a minute and click Analyze again.")
                st.stop()

    if "matches" in st.session_state:
        products = load_products()
        matches = st.session_state.matches
        df = build_report(matches, products, min_margin)
        s = summary(df)

        st.subheader("2. Margin report")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Items checked", s["items_checked"])
        m2.metric("Selling at a loss", s["loss_items"])
        m3.metric("Below min margin", s["low_margin_items"])
        m4.metric("Monthly profit lost", f"{s['profit_erosion_month']:,} EGP")

        unmatched = [m["supplier_name"] for m in matches if m["product_id"] is None]
        if unmatched:
            st.warning("Not found in your shop (skipped): " + ", ".join(unmatched))

        # glowing risk cards (top 4)
        risky = df[df["status"] != "OK"].head(4)
        for _, r in risky.iterrows():
            st.markdown(
                ui.risk_card(r["product"], r["status"], r["margin_after_pct"],
                             r["new_cost"], r["current_price"], r["suggested_price"],
                             int(r["profit_erosion_month"])),
                unsafe_allow_html=True,
            )

        # chart: margin before vs after (flagged items)
        flagged = df[df["status"] != "OK"]
        if not flagged.empty:
            fig = go.Figure()
            fig.add_bar(x=flagged["product"], y=flagged["margin_before_pct"],
                        name="Margin before", marker_color="#22d3ee")
            fig.add_bar(x=flagged["product"], y=flagged["margin_after_pct"],
                        name="Margin after supplier increase", marker_color="#fb7185")
            fig.add_hline(y=min_margin * 100, line_dash="dash", line_color="#fbbf24",
                          annotation_text="Your minimum margin")
            fig.update_layout(template="plotly_dark", barmode="group", height=360,
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              yaxis_title="Margin %", margin=dict(t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)

        sup = {m["product_id"]: m["supplier_name"] for m in matches if m["product_id"]}
        df["supplier_name"] = df["product_id"].map(sup)
        df["approve"] = ~df["needs_confirm"]

        st.caption("Tick rows to apply. 'needs_confirm' rows start unticked: check that the "
                   "supplier name matches the product. You can edit the suggested price.")
        cols = ["approve", "product", "supplier_name", "old_cost", "new_cost",
                "current_price", "margin_after_pct", "status",
                "suggested_price", "needs_confirm"]
        edited = st.data_editor(
            df[cols], hide_index=True, width="stretch",
            disabled=[c for c in cols if c not in ("approve", "suggested_price")],
            key="editor",
        )

        st.subheader("3. Approve")
        if st.button("Approve selected and update prices", type="primary"):
            chosen = edited[edited["approve"]]
            if chosen.empty:
                st.error("Nothing selected.")
            else:
                src = df.set_index("product")
                changes, announce = [], []
                for _, r in chosen.iterrows():
                    pid = int(src.loc[r["product"], "product_id"])
                    changes.append({"product_id": pid,
                                    "new_cost": float(r["new_cost"]),
                                    "new_price": float(r["suggested_price"])})
                    if r["suggested_price"] != r["current_price"]:
                        announce.append({"product": r["product"],
                                         "old_price": r["current_price"],
                                         "new_price": r["suggested_price"]})
                apply_changes(changes)
                with st.spinner("Writing customer message..."):
                    msg = generate_message(announce) if announce else ""
                st.session_state.result = {"n": len(changes), "msg": msg}
                del st.session_state["matches"]
                st.rerun()

    if "result" in st.session_state:
        res = st.session_state.result
        st.success(f"Done. {res['n']} products updated in the shop database.")
        if res["msg"]:
            st.subheader("4. Customer message (review, then copy)")
            st.code(res["msg"], language=None)
            st.link_button("Open in WhatsApp", "https://wa.me/?text=" + quote(res["msg"]))
            st.caption("AI-generated. The owner reviews and sends it. The app never sends messages by itself.")


# ---------- agent mode tab ----------
def _describe(step):
    t, r = step["tool"], step["result"]
    if "error" in r:
        return f" {r['error']}"
    if t == "parse_supplier_list":
        return f"Read {r['items_found']} items from the supplier list"
    if t == "match_products":
        return (f"{r['matched_automatically']} matched automatically, "
                f"{len(r['needs_owner_confirmation'])} need confirmation, "
                f"{len(r['unmatched'])} unmatched")
    if t == "compute_margins":
        sm = r["summary"]
        return f"{sm['loss_items']} losing money, {sm['low_margin_items']} below minimum margin"
    if t == "simulate_cost_increase":
        return (f"If costs rise {r['cost_increase_percent']:.0f}%: "
                f"{r['items_at_risk']} items at risk, {r['items_newly_at_risk']} newly")
    return ""


with tab4:
    st.subheader(" Agent mode")
    st.caption("Tell the agent what you need. It decides which tools to call, in what order, "
               "and reports back. It never changes prices: you approve in the Review & approve tab.")

    st.markdown("**1. Supplier list** (optional for what-if questions)")
    if st.button("Load sample list", key="agent_load"):
        st.session_state.agent_text = open("data/supplier_sample.txt", encoding="utf-8").read()
    st.text_area("Supplier list", key="agent_text", height=150,
                 placeholder="Paste the supplier's price list here...",
                 label_visibility="collapsed")

    st.markdown("**2. What do you want?**")
    ex = ["Analyze this list and tell me what needs my attention",
          "Which items from this list lose money? Only tell me about the SSDs",
          "What happens if the dollar rises 10%?"]
    e1, e2, e3 = st.columns(3)
    if e1.button("Full analysis", key="ex_a"):
        st.session_state.agent_req = ex[0]
    if e2.button("SSDs only", key="ex_b"):
        st.session_state.agent_req = ex[1]
    if e3.button("Dollar +10%", key="ex_c"):
        st.session_state.agent_req = ex[2]
    st.text_input("Your request", key="agent_req",
                  placeholder="e.g. What happens if the dollar rises 8%?",
                  label_visibility="collapsed")

    if st.button("Run agent", type="primary", key="agent_run"):
        txt = st.session_state.get("agent_text", "").strip()
        req = st.session_state.get("agent_req", "").strip()
        if not txt and not req:
            st.error("Paste a list or type a request first.")
        else:
            st.session_state.pop("agent_result", None)
            status = st.status("Agent is working...", expanded=True)
            n = {"i": 0}

            def show(step):
                n["i"] += 1
                status.write(f"**Step {n['i']}: `{step['tool']}`**  \n{_describe(step)}")

            try:
                st.session_state.agent_result = run_agent(
                    txt, min_margin, on_step=show, instruction=req)
                status.update(label="Agent finished", state="complete", expanded=False)
            except Exception:
                status.update(label="Agent stopped", state="error")
                st.error("The AI service is busy or its free limit was reached. "
                         "Please wait a minute and run the agent again.")

    res = st.session_state.get("agent_result")
    if res:
        st.markdown(res["answer"])
        with st.expander("What the agent did (raw tool calls)"):
            for i, s in enumerate(res["steps"], 1):
                st.markdown(f"**{i}. {s['tool']}** `{s['args']}`")
                st.json(s["result"], expanded=False)
        if res["state"].get("matches"):
            if st.button(" Send this analysis to Review & approve", key="agent_send"):
                st.session_state.matches = res["state"]["matches"]
                st.session_state.pop("result", None)
                st.success("Done. Open the Review & approve tab to approve.")
                st.rerun()