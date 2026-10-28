# Coding Agent Harness: Step 2, tool calls and an agent loop

This is a project to build a coding agent harness from scratch, one step at a time.

- **Step 1** sent a single prompt to a language model through
  [OpenRouter](https://openrouter.ai/) and printed the reply.
- **Step 2** (this stage) gives the model tools it can call, runs those tools on your
  machine, sends the results back, and keeps looping until the model gives a final answer.

The model can now explore your files and run commands on its own before it answers.

## What it does

1. Loads settings from a `.env` file.
2. Asks you for a prompt in the terminal.
3. Sends the conversation to `openai/gpt-4o` through OpenRouter, along with the
   schemas of the available tools.
4. If the model asks for one or more tool calls, the harness:
   - runs each tool with the arguments the model chose,
   - prints the tool name, its arguments and its output,
   - appends the output to the conversation as a `tool` message,
   - prints the token usage for that request,
   - and calls the model again.
5. When the model replies without asking for a tool, the harness prints the answer and stops.

## Tools

Two tools are defined in [tools.py](tools.py):

| Tool | Arguments | What it does |
|---|---|---|
| `bash` | `command` | Runs a shell command and returns its stdout and stderr |
| `read_file` | `path` | Reads a file and returns its contents |

Each tool has two parts:

- A **Python function** that does the work (`bash`, `read_file`).
- A **JSON schema** in `TOOL_SCHEMAS` that tells the model the tool's name, what it
  does and which arguments it takes.

The `TOOLS` dictionary maps each tool name to its function, so the loop can look up
whichever tool the model asks for by name.

## Project layout

| File | Purpose |
|---|---|
| [agent.py](agent.py) | Entry point. Reads your prompt and runs the agent loop |
| [llm.py](llm.py) | OpenRouter client, system prompt and the `call_llm()` function |
| [tools.py](tools.py) | Tool functions, their schemas and the `TOOLS` lookup table |

## Requirements

- Python 3.13 or newer (see `pyproject.toml`)
- An [OpenRouter API key](https://openrouter.ai/keys)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project folder:

```env
BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=your-key-here
MAX_TOKENS=2048
```

| Variable | Required | Description |
|---|---|---|
| `BASE_URL` | Yes | The OpenAI-compatible API endpoint. For OpenRouter: `https://openrouter.ai/api/v1` |
| `OPENROUTER_API_KEY` | Yes | Your OpenRouter API key |
| `MAX_TOKENS` | No | Maximum length of each reply in tokens. Defaults to `2048` |

`.env` is already listed in `.gitignore`, so your API key won't be committed.

## Usage

```bash
python agent.py
```

Example session:

```
Enter your prompt> What does tools.py do?

Tool:  bash {'command': 'ls'}
README.md
agent.py
llm.py
tools.py
...

{'prompt_tokens': 180, 'completion_tokens': 14, 'reasoning_tokens': 0, 'cached_tokens': 0}

Tool:  read_file {'path': 'tools.py'}
import json
import subprocess
...

{'prompt_tokens': 260, 'completion_tokens': 18, 'reasoning_tokens': 0, 'cached_tokens': 0}

Agent:  tools.py defines two tools the agent can use...
```

The exact tool calls, output and numbers depend on your prompt and the model.

## How it works

### Calling the model

`call_llm(messages)` in [llm.py](llm.py) sends the full message list and
`tools=TOOL_SCHEMAS` to the Chat Completions API. OpenRouter accepts the same request
format as OpenAI, so pointing `base_url` at OpenRouter is enough to reach many models
with the same code. The function returns the model's message and a token usage dict:

- `prompt_tokens`: tokens in the input (system prompt, history and tool results)
- `completion_tokens`: tokens in the model's reply
- `reasoning_tokens`: tokens spent on internal reasoning, when the model reports them
- `cached_tokens`: input tokens served from the provider's prompt cache, when reported

The reasoning and cached counts are read with `getattr`, so they show as `None` when a
model doesn't report them.

To try another model, change the `model` argument to any ID from
[OpenRouter's model list](https://openrouter.ai/models). The model needs to support
tool calling.

### The agent loop

[agent.py](agent.py) keeps a `messages` list that starts with the system prompt and
your prompt, then repeats:

1. Call the model with the whole `messages` list.
2. Append the model's reply to `messages`. The reply is converted with
   `model_dump(exclude_none=True)` so its `tool_calls` are kept in the history.
3. If the reply has no `tool_calls`, stop.
4. Otherwise, for each tool call, parse the JSON arguments, run
   `TOOLS[name](**args)`, and append a message like this:

   ```python
   {"role": "tool", "tool_call_id": tool_call.id, "content": result}
   ```

   The `tool_call_id` links each result to the call that asked for it. The API
   rejects the next request if a tool call has no matching result.
5. Go back to step 1.

Because the full history is sent on every turn, the model sees everything it has
already run and read, and can decide what to do next.

## Current limitations

- **No turn limit.** The loop runs until the model stops asking for tools. A model that
  keeps calling tools will keep the loop going and keep using tokens.
- **Commands run without confirmation.** `bash` runs whatever the model asks for with
  `shell=True`, including commands that change or delete files. Only use it in a folder
  you're happy for it to touch.
- **No command timeout.** A command that never exits, or waits for input, hangs the harness.
- **No error handling.** A missing file in `read_file`, bad JSON in the tool arguments,
  an unknown tool name, a network failure or a rate limit will stop the script with a
  Python traceback.
- **One prompt per run.** You can't send a follow-up after the agent answers. Every run
  starts fresh.
- **Usage isn't shown for the final reply.** Usage is printed after each round of tool
  calls, but the loop stops before printing it for the last request, and there's no
  total for the session.

## Roadmap

Done:

- [x] Send a prompt to a model through OpenRouter and report token usage (step 1)
- [x] Pass tool schemas to the API and handle `tool_calls` in the response
- [x] Run the requested tools and send their output back to the model
- [x] Loop until the model gives a final answer

Next:

- [ ] Add a turn limit to the loop
- [ ] Ask for confirmation before running commands that could change or delete files
- [ ] Add a timeout to `bash` and catch tool errors so they go back to the model
  instead of crashing the harness
- [ ] Keep the conversation going across prompts
- [ ] Track token usage across a whole session, and trim or summarize old history
  when it grows large
- [ ] Handle errors and retry on rate limits
- [ ] Log each step so runs can be debugged
