import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from urllib.parse import quote

import ui
from core.llm import parse_supplier_list, generate_message, ask_agent
from core.matcher import load_products, match_items
from core.margins import build_report, summary
from core.db import apply_changes
from data.seed import seed

import os
if not os.path.exists("shop.db"):
    seed()

st.set_page_config(page_title="Margin Guard", page_icon="🛡️", layout="wide")
ui.inject()

if "page" not in st.session_state:
    st.session_state.page = "landing"

# ======================= LANDING =======================
if st.session_state.page == "landing":
    ui.landing()
    _, mid, _ = st.columns([2, 1.2, 2])
    if mid.button("Get Started  →", type="primary", use_container_width=True):
        st.session_state.page = "app"
        st.rerun()
    st.stop()

# ======================= APP =======================
top1, top2 = st.columns([6, 1])
top1.markdown("## 🛡️ Margin Guard")
if top2.button("← Home"):
    st.session_state.page = "landing"
    st.rerun()
st.caption("Demo with sample shop data. The owner approves every change.")

with st.sidebar:
    st.header("Settings")
    min_margin = st.slider("Minimum margin %", 5, 40, 15) / 100
    if st.button("Reset sample shop"):
        seed()
        for k in ("matches", "result"):
            st.session_state.pop(k, None)
        st.rerun()


def load_sample():
    st.session_state.supplier_text = open(
        "data/supplier_sample.txt", encoding="utf-8"
    ).read()


tab1, tab2, tab3 = st.tabs([" Analyze", " Shop inventory", " Ask the agent"])

# ---------- inventory tab ----------
with tab2:
    st.subheader("Shop inventory (current cost and selling price)")
    inv = pd.DataFrame(load_products()).drop(columns=["id"])
    st.dataframe(inv, hide_index=True, width="stretch")

# ---------- analyze tab ----------
with tab1:
    st.subheader("1. Paste supplier price list")
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
            
# ---------- what-if agent tab ----------
with tab3:
    st.subheader(" Ask the agent (what-if)")
    st.caption("The AI calls a Python tool to do the math, then explains the result.")
    st.info(
        "**You can ask:** what-if questions about cost or dollar increases, with a percentage.\n\n"
        "Examples: *If the dollar rises 5%, which items start losing money?* · "
        "*What happens to my margins if costs rise 10%?*\n\n"
        "Other questions are not supported yet."
    )

    ex1 = "If the dollar rises 5%, which items start losing money?"
    ex2 = "What happens to my margins if costs rise 10%?"
    b1, b2 = st.columns(2)
    if b1.button(ex1, key="ex1"):
        st.session_state.q = ex1
    if b2.button(ex2, key="ex2"):
        st.session_state.q = ex2

    q = st.text_input("Your question", key="q")
    if st.button("Ask", type="primary", key="ask_btn"):
        st.session_state.agent_out = None          # purana jawab saaf
        if not q.strip():
            st.error("Type a question first.")
        else:
            with st.spinner("Agent is thinking and calling its tool..."):
                try:
                    st.session_state.agent_out = ask_agent(q, min_margin)
                except Exception as e:
                    st.error(f"Something went wrong, please ask again. ({e})")

    out = st.session_state.get("agent_out")
    if out:
        answer, calls = out
        st.markdown(answer)
        for name, args, result in calls:
            st.caption(f" Tool called: `{name}({args})`")
            if result["items"]:
                st.dataframe(pd.DataFrame(result["items"]), hide_index=True, width="stretch")
            with st.expander("Raw tool result (what Python calculated)"):
                st.json(result)