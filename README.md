# 🛡️ Margin Guard

**An AI agent that spots supplier price increases before they silently eat a small shop's margin. The agent analyzes; the shop owner approves every change.**
Built for *Agents at Work, 1st Edition* (Egyptian SME agent hackathon).

**Live demo:** https://margin-guard.streamlit.app/

> All shop data is **sample data created by me**. No real business data or market prices are used.

## The problem

Egyptian SMEs buy from suppliers whose prices follow the dollar. New price lists arrive on WhatsApp in messy Arabic and English. Checking every item by hand is slow, so owners keep selling at old prices and quietly lose money, sometimes below cost.

## How it works

- **Agent mode:** the owner pastes a supplier list (optional) and types a request, e.g. "Analyze this list" or "What happens if the dollar rises 10%?". The LLM chooses which tools to call, in what order, using each result to pick the next step (max 8 steps). Steps are shown live. Tools:
  - `parse_supplier_list`: reads messy Arabic/English text into a table.
  - `match_products`: matches supplier names to shop products (Arabic normalisation + `rapidfuzz`; unclear matches go to the LLM and need owner confirmation).
  - `compute_margins`: Python flags `LOSS` / `LOW` items and suggests rounded prices.
  - `simulate_cost_increase`: what-if for a further X% cost rise.
- **Review & approve:** a fixed workflow where the owner ticks rows and approves. **Nothing changes without the Approve click.** Approved prices are saved in SQLite and a customer message (English + Arabic) is drafted.
- **Shop inventory:** view products or upload your own CSV.

The agent only reads and analyzes; it cannot change prices. **The LLM never does the math: Python does.** (LLM: Groq, openai/gpt-oss-120b.)

## Quick start

Requires Python 3.10+ and a free Groq API key from <https://console.groq.com>.

```bash
git clone https://github.com/[YOUR_USERNAME]/margin-guard.git
cd margin-guard
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Create `.env` with `GROQ_API_KEY=your_key_here`, then:

```bash
python data/seed.py            # creates the sample shop database
streamlit run app.py
```

## Try it

1. **Get Started**, then **Agent mode**: **Load sample list**, **Run agent**.
2. **Send this analysis to Review & approve**, tick the rows (check `needs_confirm` ones first), click **Approve** to get the customer message.
3. Back in Agent mode, try *What happens if the dollar rises 10%?* with the list empty. Open "What the agent did" to see different tools were called.
4. Click **Reset sample shop** in the sidebar to restart the demo. To use your own data, upload a CSV in **Shop inventory**.

## Sample results (12-product sample shop)

| Metric | Value |
|---|---|
| Items flagged | 7 (2 `LOSS`, 5 `LOW`) |
| Monthly profit lost to the supplier increase | **14,235 EGP** |
| Monthly profit recovered at a 15% minimum margin | 17,020 EGP |
| Time to reprice (estimate) | ~30 min by hand vs ~2 min |

Profit lost = Σ (new cost − old cost) × monthly units. Suggested price = new cost / (1 − min margin), rounded up.

**Assumptions:** monthly units come from sample data and sales volume stays the same after repricing. These are demo figures, and the time saved is an estimate, not a measurement. Arabic text is AI-generated and not verified by a native speaker, so the owner should review it before sending. The free Groq tier may rate-limit: wait a minute and retry.

## Tech stack

Python · Groq · Pandas · SQLite · rapidfuzz · Streamlit · Plotly