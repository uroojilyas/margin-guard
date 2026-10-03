# 🛡️ Margin Guard

**An AI agent that spots supplier price increases before they silently eat a small shop's margin. The agent analyzes; the shop owner approves every change.**
Built for *Agents at Work, 1st Edition* (Egyptian SME agent hackathon).

**Live demo:** https://margin-guard.streamlit.app/

> **Note:** All shop data in this project is **sample data created by me**. No real business data or real market prices are used.

---

## The problem

Egyptian SMEs buy from suppliers whose prices follow the dollar. Suppliers send new price lists on WhatsApp, in messy Arabic and English. Re-checking every item by hand takes a long time, so owners often keep selling at old prices and quietly lose money, sometimes selling below cost without noticing.

## What Margin Guard does

The app has three tabs: **Agent mode**, **Review & approve** and **Shop inventory**.

**Agent mode (tool-calling agent).** The owner pastes a supplier list (optional) and types a request, for example "Analyze this list", "Only tell me about the SSDs" or "What happens if the dollar rises 10%?". The model decides which tools to call, in what order, and uses each result to choose the next step (up to 8 steps). Every step is shown live. The agent has four tools:

- `parse_supplier_list`: reads the messy Arabic/English text into a table (product, new cost).
- `match_products`: matches supplier names to the shop's products (`شاحن سامسونج 25 واط` = `Samsung 25W Charger`). Easy matches are done by code (Arabic normalisation + `rapidfuzz`); hard ones go to the LLM and are flagged for owner confirmation. The Arabic product name in the shop inventory is optional and only helps match Arabic lists.
- `compute_margins`: plain Python computes margins on the new costs, flags items as `LOSS` (negative margin), `LOW` (below the minimum margin set with the sidebar slider) or `OK`, and suggests new prices with scale-aware rounding (never rounds down).
- `simulate_cost_increase`: what-if for a further cost or dollar increase of X% on the shop's current costs.

Different requests lead to different tool calls. For example, a what-if question with no list uses only the what-if tool, while a full analysis uses all four. The agent cannot change prices.

**Review & approve (fixed workflow).** The owner either pastes a list here for a direct analysis (a fixed sequence: read, match, calculate) or sends the agent's analysis here with one click. Rows marked `needs_confirm` start unticked. The owner ticks the rows to apply and can edit suggested prices. **Nothing changes without the Approve click.** Approved prices are saved in SQLite, and the app drafts a customer price-update message (English + Arabic) to copy into WhatsApp.

**Shop inventory.** Shows the shop's products, and lets the owner upload their own inventory as CSV.

## Who does what

| Part | Responsible |
|---|---|
| Choosing which tool to call next, reading messy text, resolving unclear matches, writing messages, explaining results | LLM (Groq, openai/gpt-oss-120b) |
| All margin math, rounding, totals, what-if calculations | Python (exact and debuggable) |
| Approving every price change | The shop owner |

## Quick start

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
2. In **Agent mode**, click **Load sample list**, keep the request "Full analysis" and click **Run agent**. Watch the agent call its tools step by step. It reads 12 items, matches 7 automatically and asks for confirmation on 5.
3. Click **Send this analysis to Review & approve**, then open the **Review & approve** tab. You will see the margin report: 12 items checked, 2 selling at a loss, 5 below minimum margin, with risk cards and a margin chart.
4. Rows marked `needs_confirm` start unticked. Check that the supplier name matches the product, then tick them if correct. You can edit suggested prices.
5. Click **Approve selected and update prices** to get the customer message.
6. Back in **Agent mode**, try different requests: *Only tell me about the SSDs* (with the list loaded), or *What happens if the dollar rises 10%?* (with the list empty). Open "What the agent did" to see that different tools were called.
7. **Use your own data:** in the **Shop inventory** tab, download the CSV template, fill in your products (name, optional Arabic name, cost, price, monthly_units), upload it and click **Use this inventory**. On the shared live demo this replaces the shared sample database, so click **Reset sample shop** afterwards to restore the demo data.
8. To run the demo again, click **Reset sample shop** in the sidebar (approving saves the new costs, so the same list would show nothing the second time).

### What you can ask the agent

Requests about the supplier list, margins and cost or dollar increases, for example:

- *Analyze this list and tell me what needs my attention*
- *Which items from this list lose money? Only tell me about the SSDs*
- *What happens if the dollar rises 10%?* (no list needed)

Requests outside margins, prices, costs and supplier lists get a short message about what the agent can do.

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

**Assumptions:** monthly units come from the sample data, and sales volume is assumed to stay the same after repricing. These are demo figures, not measurements from a real shop. The agent's tools are fixed (four tools, up to 8 steps per request), it only reads and analyzes, and the owner makes every change. Arabic text is AI-generated and was not verified by a native speaker, so the owner should review it before sending. Uses a free Groq tier: if the limit is reached, wait a minute and try again.

**Time saved (estimate):** Repricing the 12-item sample by hand is estimated at about 30 minutes (roughly 2.5 minutes per item for matching, margin calculation and pricing, plus about 5 minutes to write the customer message). With Margin Guard the same flow takes about 2 minutes. This is an estimate on the sample shop, not a measured result. Real shops with 100+ items would save proportionally more.

## Tech stack

Python · Groq (openai/gpt-oss-120b) · Pandas · SQLite · rapidfuzz · Streamlit · Plotly