import json
import os
from dotenv import load_dotenv

# load environment variables from .env
load_dotenv()

import sys
from openai import OpenAI

client = OpenAI(
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

user_input = input("Enter your prompt> ")

SYSTEM_PROMPT = """
    You are a coding agent. Your job is to code. Always code.
    Use the bash tool to inspect files.
    Answer back to the user once exploration is done
"""

BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash", 
        "description": "Run a shell command and return it's output.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to run",
                }
            },
            "required": ["command"],
        }
    }
}

MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2048"))

# calling gpt-4o from openrouter
response = client.chat.completions.create(
    model="openai/gpt-4o",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ],
    max_tokens=MAX_TOKENS, 
) 
# [<leader>aa: ask, <leader>ae: edit]

output = response.choices[0].message.content

completion_details = response.usage.completion_tokens_details
prompt_details = response.usage.prompt_tokens_details

usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "reasoning_tokens": getattr(completion_details, "reasoning_tokens", None),
        "cached_tokens": getattr(prompt_details, "cached_tokens", None),
    }

print("\nAgent: ", output, "\n")
print(usage)