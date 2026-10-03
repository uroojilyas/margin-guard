import streamlit as st
from urllib.parse import quote

from core.llm import parse_supplier_list, generate_message
from core.matcher import load_products, match_items
from core.margins import build_report, summary
from core.db import apply_changes
from data.seed import seed

st.set_page_config(page_title="Margin Guard", page_icon="🛡️", layout="wide")
st.title("🛡️ Margin Guard")
st.caption("Catch supplier price increases before they eat your margin. Demo with sample shop data.")

# ---------- sidebar ----------
with st.sidebar:
    st.header("Settings")
    min_margin = st.slider("Minimum margin %", 5, 40, 15) / 100
    if st.button("Reset sample shop"):
        seed()
        st.session_state.clear()
        st.rerun()


def load_sample():
    st.session_state.supplier_text = open(
        "data/supplier_sample.txt", encoding="utf-8"
    ).read()


# ---------- 1. input ----------
st.subheader("1. Paste supplier price list")
st.text_area("Supplier list", key="supplier_text", height=220,
             placeholder="Paste the WhatsApp price list here...")
c1, c2 = st.columns([1, 5])
c1.button("Load sample", on_click=load_sample)

if c2.button("Analyze", type="primary"):
    text = st.session_state.get("supplier_text", "").strip()
    if not text:
        st.error("Paste a list first (or click Load sample).")
    else:
        with st.spinner("Reading the list and matching products..."):
            parsed = parse_supplier_list(text)
            st.session_state.matches = match_items(parsed, load_products())
        st.session_state.pop("result", None)

# ---------- 2. report ----------
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

    # supplier name next to our product, so the owner can verify matches
    sup = {m["product_id"]: m["supplier_name"] for m in matches if m["product_id"]}
    df["supplier_name"] = df["product_id"].map(sup)
    df["approve"] = ~df["needs_confirm"]   # unsure matches start unticked

    st.caption("Tick rows to apply. Rows with 'needs_confirm' start unticked: "
               "check the supplier name matches the product first. "
               "You can edit the suggested price.")

    cols = ["approve", "product", "supplier_name", "old_cost", "new_cost",
            "current_price", "margin_after_pct", "status",
            "suggested_price", "needs_confirm"]
    edited = st.data_editor(
        df[cols],
        hide_index=True,
        use_container_width=True,
        disabled=[c for c in cols if c not in ("approve", "suggested_price")],
        key="editor",
    )

    # ---------- 3. approve ----------
    st.subheader("3. Approve")
    if st.button("✅ Approve selected and update prices", type="primary"):
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

# ---------- 4. result ----------
if "result" in st.session_state:
    res = st.session_state.result
    st.success(f"Done. {res['n']} products updated in the shop database.")
    if res["msg"]:
        st.subheader("4. Customer message (review, then copy)")
        st.code(res["msg"], language=None)
        st.link_button("Open in WhatsApp", "https://wa.me/?text=" + quote(res["msg"]))
        st.caption("AI-generated. The owner reviews and sends it. The app never sends messages by itself.")