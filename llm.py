import os
from dotenv import load_dotenv
from openai import OpenAI

from tools import TOOL_SCHEMAS

# load environment variables from .env
load_dotenv()

client = OpenAI(
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

SYSTEM_PROMPT = """
    You are a coding agent. Your job is to code. Always code.
    Use the bash tool to inspect files.
    Answer back to the user once exploration is done
"""

MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2048"))


def call_llm(messages):
    # calling gpt-4o from openrouter
    response = client.chat.completions.create(
        model="openai/gpt-4o",
        messages=messages,
        max_tokens=MAX_TOKENS,
        tools=TOOL_SCHEMAS,
    )

    completion_details = response.usage.completion_tokens_details
    prompt_details = response.usage.prompt_tokens_details

    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "reasoning_tokens": getattr(completion_details, "reasoning_tokens", None),
        "cached_tokens": getattr(prompt_details, "cached_tokens", None),
    }

    return response.choices[0].message, usage
