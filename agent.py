import json
import argparse
# import commands
# import compact
# import history
# import session

from llm import SYSTEM_PROMPT, call_llm
from tools import TOOLS

user_input = input("Enter your prompt> ")

messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
]

while True:
    message, usage = call_llm(messages)
    messages.append(message.model_dump(exclude_none=True))

    if message.content:
        print("\nAgent: ", message.content, "\n")

    if not message.tool_calls:
        break

    for tool_call in message.tool_calls:
        args = json.loads(tool_call.function.arguments)
        result = TOOLS[tool_call.function.name](**args)
        print("Tool: ", tool_call.function.name, args)
        print(result, "\n")

        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": result,
        })

    print(usage)