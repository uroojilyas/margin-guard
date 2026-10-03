from core.llm import parse_supplier_list
from core.matcher import load_products, match_items

text = open("data/supplier_sample.txt", encoding="utf-8").read()
parsed = parse_supplier_list(text)
products = load_products()

for m in match_items(parsed, products):
    print(f'{m["status"]:9} {m["score"]:3}  {m["supplier_name"][:35]:35} -> {m["product_name"]}')