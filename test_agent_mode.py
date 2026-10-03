from data.seed import seed
from core.agent import run_agent

seed()   # shop ko fresh sample state par laata hai
text = open("data/supplier_sample.txt", encoding="utf-8").read()
out = run_agent(text, 0.15)

print("TOOLS CALLED, IN ORDER:")
for i, s in enumerate(out["steps"], 1):
    print(f"  {i}. {s['tool']} {s['args']}")
print("\nANSWER:\n" + out["answer"])