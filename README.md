# 🛡️ Margin Guard

**An AI agent that catches supplier price increases before they silently eat a small shop's margin.**
Built for *Agents at Work, 1st Edition* (Egyptian SME agent hackathon).

- **Live demo:** 
- **Demo video:** 

> **Note:** All shop data in this project is **sample data created by me**. No real business data or real market prices are used.

---

## The problem

Egyptian SMEs buy from suppliers whose prices follow the dollar. Suppliers send new price lists on WhatsApp, in messy Arabic and English. Re-checking every item by hand takes hours, so owners often keep selling at old prices and quietly lose money, sometimes selling below cost without noticing.

## What Margin Guard does

1. **Paste** the supplier's new price list (WhatsApp-style text, Arabic or English).
2. **Read:** an LLM (Groq / Llama) turns the messy text into a clean table (product, new cost).
3. **Match:** supplier names are matched to the shop's products (`شاحن سامسونج 25 واط` = `Samsung 25W Charger`). Easy matches are done by code (Arabic normalisation + `rapidfuzz`). Hard ones go to the LLM and are flagged **needs_confirm** for the owner.
4. **Calculate:** plain Python computes margins on the new cost and flags items as `LOSS` (negative margin), `LOW` (below the owner's minimum margin) or `OK`.
5. **Suggest:** new selling prices that reach the minimum margin, with scale-aware rounding (never rounds down).
6. **Approve:** the owner ticks the rows to apply. **Nothing changes without this click.** Approved prices are saved in SQLite.
7. **Announce:** the agent drafts a customer price-update message (English + Arabic) to copy into WhatsApp.
8. **Ask the agent (what-if):** the owner asks "If the dollar rises 5%, which items start losing money?" The LLM calls a Python tool (`simulate_cost_increase`), Python does the math, and the LLM explains the result.

## Who does what

| Part | Responsible |
|---|---|
| Reading messy text, resolving unclear matches, writing messages, understanding what-if questions | LLM (Groq, Llama 3.3 70B) |
| All margin math, rounding, totals | Python (exact and debuggable) |
| Approving every price change | The shop owner |

## Quick start (about 5 minutes)

Requires Python 3.10+ and a free Groq API key from <https://console.groq.com> (no card needed).

```bash
git clone https://github.com/[YOUR_USERNAME]/margin-guard.git
cd margin-guard

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

Create a file named `.env` in the project root:

```
GROQ_API_KEY=your_key_here
```

Then run:

```bash
python data/seed.py            # creates the sample shop database (shop.db)
streamlit run app.py
```

## How to try it (judge walkthrough)

1. Click **Get Started**.
2. In **Analyze**, click **Load sample**, then **Analyze**.
3. You will see the margin report: 12 items checked, 2 selling at a loss, 5 below minimum margin, with glowing risk cards and a margin chart.
4. Rows marked `needs_confirm` start unticked. Check that the supplier name matches the product, then tick them if correct. You can edit suggested prices.
5. Click **Approve selected and update prices** to get the customer message.
6. Open **Ask the agent** and try: *If the dollar rises 5%, which items start losing money?*
7. To run the demo again, click **Reset sample shop** in the sidebar (approving saves the new costs, so the same list would show nothing the second time).

### What you can ask the agent

What-if questions about cost or dollar increases **with a percentage**, for example:

- *If the dollar rises 5%, which items start losing money?*
- *What happens to my margins if costs rise 10%?*
- *How much profit would I lose if supplier prices go up 15%?*

Other questions get a help message listing what is supported.

## Sample results (sample shop, 12 products)

| Metric | Value |
|---|---|
| Items flagged | 7 (2 `LOSS`, 5 `LOW`) |
| Monthly profit lost to the supplier increase | **14,235 EGP** |
| Monthly profit recovered by repricing to a 15% minimum margin | 17,020 EGP |

How these are calculated:

- **Margin** = (price − cost) / price
- **Monthly profit lost** = Σ (new cost − old cost) × monthly units sold, over flagged items
- **Suggested price** = new cost / (1 − minimum margin), rounded **up**: nearest 1 EGP under 50, 5 under 200, 10 under 1000, 50 above
- **Profit recovered** = Σ (suggested price − current price) × monthly units

**Assumptions:** monthly units come from the sample data, and sales volume is assumed to stay the same after repricing. These are demo figures, not measurements from a real shop.

**Time saved:** repricing the 12-item sample by hand took me [X] minutes. With Margin Guard it took [Y] minutes. (Timed by me on the sample shop.)


## Safety and design choices

- **Human approval:** prices change only after the owner ticks and approves.
- **Capacity check:** names with different numbers (e.g. `SSD 512GB` vs `SSD 1TB`) are penalised in matching so they are not mixed up.
- **Uncertain matches** are flagged `needs_confirm` and start unticked.
- **LLM never does the math.** It reads, matches and writes. Python computes every number.
- **No automatic sending:** the app never messages anyone. The owner copies the drafted message into WhatsApp.

## Tech stack

Python · Groq (Llama 3.3 70B) · Pandas · SQLite · rapidfuzz · Streamlit · Plotly · Git/GitHub


## Author

Urooj Ilyas, Pakistan.
