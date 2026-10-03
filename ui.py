import streamlit as st

CSS = """
<style>
#MainMenu, footer {visibility:hidden;}
[data-testid="stToolbar"], [data-testid="stDecoration"] {display:none;}
header {background:transparent !important;}
.block-container {padding-top:1.5rem; max-width:1150px; position:relative; z-index:1;}
.stApp {background: radial-gradient(1200px 600px at 10% -10%, #1b2a6b55, transparent),
        radial-gradient(900px 500px at 100% 0%, #0e7490440, transparent), #0b1020;}

/* floating background blobs */
.blob {position:fixed; border-radius:50%; filter:blur(80px); opacity:.35;
       pointer-events:none; z-index:0; animation:float 12s ease-in-out infinite;}
.b1 {width:380px; height:380px; background:#6366f1; top:8%; left:-6%;}
.b2 {width:320px; height:320px; background:#22d3ee; bottom:5%; right:-4%; animation-delay:-5s;}
.b3 {width:240px; height:240px; background:#ef4444; top:55%; left:40%; opacity:.18; animation-delay:-8s;}
@keyframes float {0%,100%{transform:translateY(0) scale(1);} 50%{transform:translateY(-40px) scale(1.08);}}

/* hero */
.hero {text-align:center; padding:3.5rem 0 1.5rem;}
.shield {font-size:4.5rem; display:inline-block; animation:bob 3s ease-in-out infinite;
         filter:drop-shadow(0 0 25px #22d3ee99);}
@keyframes bob {0%,100%{transform:translateY(0);} 50%{transform:translateY(-14px);}}
.hero h1 {font-size:4rem; font-weight:800; margin:.4rem 0; letter-spacing:-1px;
          background:linear-gradient(90deg,#22d3ee,#818cf8,#f472b6,#22d3ee);
          background-size:300% 100%; -webkit-background-clip:text; background-clip:text;
          -webkit-text-fill-color:transparent; animation:shift 6s linear infinite;}
@keyframes shift {to{background-position:300% 0;}}
.tag {font-size:1.35rem; color:#b6bddb; max-width:640px; margin:0 auto; animation:fade 1.2s both;}
@keyframes fade {from{opacity:0; transform:translateY(20px);} to{opacity:1; transform:none;}}

/* ticking counter */
@property --n {syntax:'<integer>'; initial-value:0; inherits:false;}
.stat {text-align:center; margin:2rem 0 1rem;}
.count {font-size:3.4rem; font-weight:800; color:#fb7185; animation:count 2.8s ease-out forwards;
        counter-reset:num var(--n); text-shadow:0 0 30px #ef444488;}
.count::after {content:counter(num) " EGP";}
@keyframes count {to {--n:14235;}}
.statlabel {color:#9aa3c7; font-size:1rem;}

/* step cards */
.cards {display:flex; gap:1.2rem; margin:2rem 0; flex-wrap:wrap;}
.card {flex:1; min-width:220px; padding:1.4rem; border-radius:18px;
       background:linear-gradient(145deg,#ffffff10,#ffffff05); border:1px solid #ffffff18;
       backdrop-filter:blur(8px); animation:fade .9s both; transition:.3s;}
.card:hover {transform:translateY(-6px); border-color:#22d3ee88; box-shadow:0 10px 40px #22d3ee22;}
.card:nth-child(1){animation-delay:.2s;} .card:nth-child(2){animation-delay:.5s;} .card:nth-child(3){animation-delay:.8s;}
.card .ic {font-size:2rem;} .card h4 {margin:.5rem 0 .3rem; color:#fff;} .card p {color:#aab2d5; margin:0; font-size:.95rem;}

/* buttons */
div.stButton > button[kind="primary"] {
  background:linear-gradient(90deg,#22d3ee,#6366f1); border:none; color:#fff; font-weight:700;
  padding:.8rem 1.5rem; border-radius:14px; font-size:1.1rem; animation:pulse 2s infinite;}
div.stButton > button[kind="primary"]:hover {transform:scale(1.04);}
@keyframes pulse {0%{box-shadow:0 0 0 0 #22d3ee77;} 70%{box-shadow:0 0 0 18px #22d3ee00;} 100%{box-shadow:0 0 0 0 #22d3ee00;}}

/* app page */
div[data-testid="stMetric"] {background:linear-gradient(145deg,#ffffff10,#ffffff05);
  border:1px solid #ffffff18; padding:1rem 1.2rem; border-radius:16px;}
.risk {padding:1rem 1.2rem; border-radius:16px; background:#ef444414; border:1px solid #ef4444aa;
       animation:glow 2s ease-in-out infinite; margin-bottom:.8rem;}
.risk.low {background:#f59e0b14; border-color:#f59e0baa; animation:none;}
@keyframes glow {0%,100%{box-shadow:0 0 6px #ef444455;} 50%{box-shadow:0 0 24px #ef4444aa;}}
.risk b {font-size:1.05rem;} .risk span {color:#c5cbe8; font-size:.9rem;}
.badge {float:right; font-weight:800; color:#fb7185;}
</style>
"""

LANDING = """
<div class="blob b1"></div><div class="blob b2"></div><div class="blob b3"></div>
<div class="hero">
<div class="shield">🛡️</div>
<h1>Margin Guard</h1>
<div class="tag">Supplier prices went up. Yours didn't. Catch silent losses in minutes, not hours.</div>
</div>
<div class="stat"><div class="count"></div>
<div class="statlabel">lost per month on our sample shop after one supplier price update</div></div>
<div class="cards">
<div class="card"><div class="ic"></div><h4>Paste the supplier list</h4><p>Messy WhatsApp text, Arabic or English. The AI reads it.</p></div>
<div class="card"><div class="ic"></div><h4>See what's losing money</h4><p>Exact margin math on every item. Risky ones glow red.</p></div>
<div class="card"><div class="ic"></div><h4>Approve new prices</h4><p>You stay in control. Then get a customer message ready to send.</p></div>
</div>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


def landing():
    st.markdown(LANDING, unsafe_allow_html=True)


def risk_card(product, status, margin_after, new_cost, price, suggested, erosion):
    cls = "risk" if status == "LOSS" else "risk low"
    label = "LOSING MONEY" if status == "LOSS" else "LOW MARGIN"
    return (
        f'<div class="{cls}"><span class="badge">{label}</span>'
        f"<b>{product}</b><br>"
        f"<span>Cost now {new_cost:.0f} | price {price:.0f} | margin {margin_after:.1f}% "
        f"| suggested <b>{suggested:.0f}</b> EGP | -{erosion:,} EGP/month</span></div>"
    )

SIDEBAR_CSS = """
<style>
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0f1730 0%, #0b1020 100%);
  border-right: 1px solid #ffffff14;}
section[data-testid="stSidebar"] .block-container {padding-top:1rem;}
.sb-brand {display:flex; align-items:center; gap:.7rem; padding:.4rem 0 1rem;
  border-bottom:1px solid #ffffff14; margin-bottom:1rem;}
.sb-logo {font-size:2rem; filter:drop-shadow(0 0 12px #22d3ee99);}
.sb-name {font-size:1.25rem; font-weight:800; line-height:1.1;
  background:linear-gradient(90deg,#22d3ee,#818cf8); -webkit-background-clip:text;
  background-clip:text; -webkit-text-fill-color:transparent;}
.sb-sub {font-size:.75rem; color:#8f98bf;}
.sb-label {font-size:.72rem; letter-spacing:.12em; text-transform:uppercase;
  color:#7f89b3; margin:1.1rem 0 .5rem; font-weight:700;}
.sb-card {padding:.9rem 1rem; border-radius:14px; border:1px solid #ffffff18;
  background:linear-gradient(145deg,#ffffff10,#ffffff05);}
.sb-shop {font-weight:700; color:#fff; font-size:1rem;}
.sb-tag {display:inline-block; font-size:.65rem; padding:.1rem .5rem; border-radius:99px;
  background:#22d3ee22; color:#22d3ee; border:1px solid #22d3ee55; margin-left:.4rem;
  vertical-align:middle;}
.sb-grid {display:grid; grid-template-columns:1fr 1fr 1fr; gap:.5rem; margin-top:.8rem;}
.sb-stat {text-align:center; padding:.5rem .2rem; border-radius:10px; background:#ffffff08;}
.sb-stat b {display:block; font-size:1.05rem; color:#e6e9f5;}
.sb-stat span {font-size:.65rem; color:#8f98bf;}
.sb-step {display:flex; gap:.7rem; align-items:flex-start; margin:.55rem 0;
  font-size:.85rem; color:#b6bddb;}
.sb-num {min-width:1.5rem; height:1.5rem; border-radius:50%; display:flex;
  align-items:center; justify-content:center; font-size:.75rem; font-weight:800;
  background:linear-gradient(135deg,#22d3ee,#6366f1); color:#fff;}
.sb-foot {margin-top:1.2rem; padding-top:.8rem; border-top:1px solid #ffffff14;
  font-size:.7rem; color:#6f789f; line-height:1.5;}
</style>
"""


def sidebar_head():
    st.markdown(SIDEBAR_CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="sb-brand"><div class="sb-logo">🛡️</div>'
        '<div><div class="sb-name">Margin Guard</div>'
        '<div class="sb-sub">Protect your margins</div></div></div>',
        unsafe_allow_html=True,
    )


def sidebar_shop(n_products, avg_margin, units):
    st.markdown(
        '<div class="sb-label">Your shop</div>'
        '<div class="sb-card">'
        '<div class="sb-shop">Mobile Accessories<span class="sb-tag">SAMPLE</span></div>'
        '<div class="sb-grid">'
        f'<div class="sb-stat"><b>{n_products}</b><span>Products</span></div>'
        f'<div class="sb-stat"><b>{avg_margin:.0f}%</b><span>Avg margin</span></div>'
        f'<div class="sb-stat"><b>{units:,}</b><span>Units/mo</span></div>'
        '</div></div>',
        unsafe_allow_html=True,
    )


def sidebar_steps():
    st.markdown(
        '<div class="sb-label">How it works</div>'
        '<div class="sb-step"><div class="sb-num">1</div><div>Paste the supplier list</div></div>'
        '<div class="sb-step"><div class="sb-num">2</div><div>AI reads and matches products</div></div>'
        '<div class="sb-step"><div class="sb-num">3</div><div>Python checks every margin</div></div>'
        '<div class="sb-step"><div class="sb-num">4</div><div>You approve new prices</div></div>'
        '<div class="sb-foot">Demo with sample data.<br>The owner approves every change.<br>',
        unsafe_allow_html=True,
    )