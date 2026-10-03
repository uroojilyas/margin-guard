from core.llm import parse_supplier_list

text = open("data/supplier_sample.txt", encoding="utf-8").read()
for item in parse_supplier_list(text):
    print(item)