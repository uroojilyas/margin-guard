from core.llm import ask_agent

answer, calls = ask_agent("If the dollar rises 5%, which items start losing money?")
print(calls[0][0], calls[0][1])
print(answer)