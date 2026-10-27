# Coding Agent Harness: Step 1, a basic chat call

This is the first step of a project to build a coding agent harness from scratch.
The script sends one prompt to a language model through [OpenRouter](https://openrouter.ai/),
prints the reply, and reports how many tokens the request used.

There's no agent loop yet. The script makes a single request and exits. It's the
foundation for the steps that follow: tool calls, a loop, and context management.

## What it does

1. Loads settings from a `.env` file.
2. Asks you for a prompt in the terminal.
3. Sends the prompt to `openai/gpt-4o` through OpenRouter, with a system prompt that
   sets the model up as a coding agent.
4. Prints the model's answer.
5. Prints token usage for the request:
   - `prompt_tokens`: tokens in the input (system prompt and your message)
   - `completion_tokens`: tokens in the model's reply
   - `reasoning_tokens`: tokens spent on internal reasoning, when the model reports them
   - `cached_tokens`: input tokens served from the provider's prompt cache, when reported

The reasoning and cached counts are read with `getattr`, so the script still works when
a model doesn't report them. They show as `None` in that case.

## Requirements

- Python 3.9 or newer
- An [OpenRouter API key](https://openrouter.ai/keys)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install openai python-dotenv
```

Create a `.env` file next to the script:

```env
BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=your-key-here
MAX_TOKENS=2048
```

| Variable | Required | Description |
|---|---|---|
| `BASE_URL` | Yes | The OpenAI-compatible API endpoint. For OpenRouter: `https://openrouter.ai/api/v1` |
| `OPENROUTER_API_KEY` | Yes | Your OpenRouter API key |
| `MAX_TOKENS` | No | Maximum length of the reply in tokens. Defaults to `2048` |

Add `.env` to your `.gitignore` so your API key never gets committed.

## Usage

```bash
python main.py
```

(Replace `main.py` with your script's file name.)

Example session:

```
Enter your prompt> Write a Python function that reverses a string

Agent:  Here's a simple function...

{'prompt_tokens': 52, 'completion_tokens': 87, 'reasoning_tokens': 0, 'cached_tokens': 0}
```

The numbers depend on your prompt and on the model's answer.

## How it works

The script uses the official `openai` Python package. OpenRouter accepts the same
request format as OpenAI's Chat Completions API, so pointing `base_url` at
OpenRouter is enough to reach many different models with the same code.

The model name `openai/gpt-4o` uses OpenRouter's `provider/model` format. To try
another model, change the `model` argument to any ID from
[OpenRouter's model list](https://openrouter.ai/models).

The request sends two messages:

- A **system** message: standing instructions that tell the model it's a coding agent.
- A **user** message: the prompt you typed.

## Current limitations

- **One request per run.** The script doesn't keep a conversation going. Every run
  starts fresh.
- **The bash tool isn't used yet.** `BASH_TOOL` is defined, but it isn't passed to
  the API call (there's no `tools=[BASH_TOOL]` argument), and nothing runs the
  commands the model asks for. The system prompt mentions the bash tool, but for now
  the model can't call it.
- **No error handling.** A missing API key, a network failure or a rate limit will
  stop the script with a Python traceback.

## Roadmap

These are the next steps toward a full coding agent harness:

- [ ] Pass `BASH_TOOL` to the API and handle `tool_calls` in the response
- [ ] Run the requested commands and send their output back to the model
- [ ] Add a loop so the agent keeps going until it gives a final answer, with a turn limit
- [ ] Ask for confirmation before running commands that could change or delete files
- [ ] Keep the conversation history across turns
- [ ] Track token usage across a whole session, and trim or summarize old history
  when it grows large
- [ ] Handle errors and retry on rate limits
- [ ] Log each step so runs can be debugged
