import json
import os
import time
from dataclasses import dataclass, field

import anthropic
import openai
from dotenv import load_dotenv

from skills import skills_prompt
from tools import TOOL_SCHEMAS

# load environment variables from .env
load_dotenv()

SYSTEM_PROMPT = f"""You are a coding agent working in the user's project folder.
Use the bash tool to explore and run commands, and read_file to read files.
For anything that needs a web browser, use the browser tool (ego-browser).
Once you have explored enough, answer the user.

Available skills (call read_skill to load one before doing a matching task):
{skills_prompt()}
"""

PROVIDER = os.getenv("PROVIDER", "openrouter").lower()
MODEL = os.getenv("MODEL")
EFFORT = os.getenv("EFFORT")  # anthropic only: low | medium | high | xhigh | max

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))
MAX_WAIT = 8  # seconds

# errors that can pass if we wait: rate limits, timeouts, dropped connections, 5xx.
# Anything else (bad key, 402 out of credits, bad request) won't fix itself.
RETRYABLE = (
    openai.RateLimitError,
    openai.APIConnectionError,  # includes APITimeoutError
    openai.InternalServerError,
    anthropic.RateLimitError,
    anthropic.APIConnectionError,
    anthropic.InternalServerError,
)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # JSON text, as the model wrote it


@dataclass
class Reply:
    """One model response, the same shape whichever provider produced it."""
    message: dict  # the provider's own history entry, appended to messages as-is
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    truncated: bool = False  # hit MAX_TOKENS
    refused: bool = False  # the model declined the request


def _retry_wait(error, attempt):
    """Seconds to wait before the next try: the server's retry-after if it sent one,
    otherwise exponential backoff (2, 4, 8, ...)."""
    response = getattr(error, "response", None)
    if response is not None:
        try:
            return min(float(response.headers["retry-after"]), MAX_WAIT)
        except (KeyError, ValueError):
            pass
    return min(2 ** (attempt + 1), MAX_WAIT)


def with_retries(request, on_retry=None):
    # on_retry(error, wait, attempt, max_retries) is called before each wait, so the UI can show it
    for attempt in range(MAX_RETRIES + 1):
        try:
            return request()
        except RETRYABLE as e:
            if attempt == MAX_RETRIES:
                raise
            wait = _retry_wait(e, attempt)
            if on_retry:
                on_retry(e, wait, attempt + 1, MAX_RETRIES)
            time.sleep(wait)


class OpenRouterProvider:
    """Any OpenAI-compatible endpoint (OpenRouter by default), using the chat format."""

    name = "openrouter"

    def __init__(self, model):
        self.client = openai.OpenAI(
            base_url=os.getenv("BASE_URL"),
            api_key=os.getenv("OPENROUTER_API_KEY"),
            max_retries=0,  # with_retries does its own retries
        )
        self.model = model
        self.max_tokens = int(os.getenv("MAX_TOKENS", "1000"))

    def new_conversation(self):
        return [{"role": "system", "content": SYSTEM_PROMPT}]

    def user_message(self, text):
        return {"role": "user", "content": text}

    def call(self, messages, reminder, on_retry=None):
        # the reminder goes at the end and is not kept, so the prefix stays cacheable
        response = with_retries(lambda: self.client.chat.completions.create(
            model=self.model,
            messages=messages + [{"role": "user", "content": reminder}],
            max_tokens=self.max_tokens,
            tools=TOOL_SCHEMAS,
        ), on_retry)

        choice = response.choices[0]
        message = choice.message
        completion_details = response.usage.completion_tokens_details
        prompt_details = response.usage.prompt_tokens_details

        return Reply(
            message=message.model_dump(exclude_none=True),
            text=message.content or "",
            tool_calls=[
                ToolCall(tc.id, tc.function.name, tc.function.arguments or "{}")
                for tc in message.tool_calls or []
            ],
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "reasoning_tokens": getattr(completion_details, "reasoning_tokens", None),
                "cached_tokens": getattr(prompt_details, "cached_tokens", None),
            },
            truncated=choice.finish_reason == "length",
        )

    def tool_results(self, results):
        # one "tool" message per result
        return [
            {"role": "tool", "tool_call_id": call_id, "content": content}
            for call_id, content, _ in results
        ]


class AnthropicProvider:
    """Anthropic's Messages API, called directly with the official SDK."""

    name = "anthropic"

    # models that accept server-side fallbacks: if one declines a request on safety
    # grounds, the API reruns it on another model instead of just stopping
    FALLBACK_MODELS = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}

    def __init__(self, model):
        self.client = anthropic.Anthropic(max_retries=0)  # key from ANTHROPIC_API_KEY
        self.model = model or "claude-opus-5-5"
        # Claude's thinking counts towards max_tokens, so it needs more room
        self.max_tokens = int(os.getenv("MAX_TOKENS", "16000"))
        self.tools = [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "input_schema": t["function"]["parameters"],
            }
            for t in TOOL_SCHEMAS
        ]

    def new_conversation(self):
        return []  # the system prompt is a separate parameter

    def user_message(self, text):
        return {"role": "user", "content": [{"type": "text", "text": text}]}

    def call(self, messages, reminder, on_retry=None):
        # Current Claude models check that the history they wrote their thinking after
        # never changes. A reminder sent once and then dropped would be such a change,
        # so it is added to the latest user message and stays in the history.
        messages[-1]["content"].append({"type": "text", "text": reminder})

        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": SYSTEM_PROMPT,
            "messages": messages,
            "tools": self.tools,
            "cache_control": {"type": "ephemeral"},  # cache the history for the next request
        }
        if EFFORT:
            kwargs["output_config"] = {"effort": EFFORT}

        if self.model in self.FALLBACK_MODELS:
            create = self.client.beta.messages.create
            kwargs["betas"] = ["server-side-fallback-2026-07-01"]
            kwargs["fallbacks"] = "default"
        else:
            create = self.client.messages.create

        response = with_retries(lambda: create(**kwargs), on_retry)

        u = response.usage
        cached = u.cache_read_input_tokens or 0
        return Reply(
            # keep every block (thinking, fallback, ...) unchanged for the next request
            message={"role": "assistant", "content": response.content},
            text="".join(b.text for b in response.content if b.type == "text"),
            tool_calls=[
                ToolCall(b.id, b.name, json.dumps(b.input))
                for b in response.content if b.type == "tool_use"
            ],
            usage={
                # input_tokens only counts the uncached part
                "prompt_tokens": u.input_tokens + cached + (u.cache_creation_input_tokens or 0),
                "completion_tokens": u.output_tokens,
                "reasoning_tokens": getattr(u.output_tokens_details, "thinking_tokens", None),
                "cached_tokens": cached,
            },
            truncated=response.stop_reason == "max_tokens",
            refused=response.stop_reason == "refusal",
        )

    def tool_results(self, results):
        # all results go back together in one user message
        return [{
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": call_id,
                    "content": content or "(no output)",  # empty text is rejected
                    "is_error": is_error,
                }
                for call_id, content, is_error in results
            ],
        }]


def make_provider():
    if PROVIDER == "anthropic":
        return AnthropicProvider(MODEL)
    if PROVIDER == "openrouter":
        return OpenRouterProvider(MODEL)
    raise SystemExit(f"Unknown PROVIDER '{PROVIDER}' in .env (use openrouter or anthropic)")


provider = make_provider()
