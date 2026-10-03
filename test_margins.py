import pandas as pd
from core.llm import parse_supplier_list
from core.matcher import load_products, match_items
from core.margins import build_report, summary

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", None)

text = open("data/supplier_sample.txt", encoding="utf-8").read()
products = load_products()
matches = match_items(parse_supplier_list(text), products)

df = build_report(matches, products)
print(df[["product", "old_cost", "new_cost", "current_price",
          "margin_after_pct", "status", "suggested_price",
          "profit_erosion_month", "needs_confirm"]])
print()
print(summary(df))