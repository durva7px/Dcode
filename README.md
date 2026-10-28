# Coding Agent Harness: Step 3, skills

This is a project to build a coding agent harness from scratch, one step at a time.

- **Step 1** sent a single prompt to a language model through
  [OpenRouter](https://openrouter.ai/) and printed the reply.
- **Step 2** gave the model tools it can call, ran those tools on your machine, sent the
  results back, and kept looping until the model gave a final answer.
- **Step 3** (this stage) adds **skills**: reusable instructions in `SKILL.md` files that
  the model loads only when a task needs them.

The model can explore your files and run commands on its own before it answers, and it
can follow your own playbooks for tasks like committing.

## What it does

1. Loads settings from a `.env` file.
2. Asks you for a prompt in the terminal.
3. Sends the conversation to the model set in `MODEL`, through OpenRouter or directly to
   Anthropic (see [Calling the model](#calling-the-model)), along with the
   schemas of the available tools.
4. If the model asks for one or more tool calls, the harness:
   - runs each tool with the arguments the model chose,
   - prints the tool name, its arguments and its output,
   - appends the output to the conversation as a `tool` message,
   - prints the token usage for that request,
   - and calls the model again.
5. When the model replies without asking for a tool, the harness prints the answer and stops.

## Tools

Four tools are defined in [tools.py](tools.py):

| Tool | Arguments | What it does |
|---|---|---|
| `bash` | `command` | Runs a shell command and returns its stdout and stderr |
| `read_file` | `path` | Reads a file (as UTF-8) and returns its contents |
| `read_skill` | `name` | Returns the full `SKILL.md` of a skill (see [Skills](#skills)) |
| `browser` | `script` | Runs a JavaScript script in [ego-browser](#browser-ego-browser) and returns its output |

Each tool has two parts:

- A **Python function** that does the work (`bash`, `read_file`, `read_skill`, `browser`).
- A **JSON schema** in `TOOL_SCHEMAS` that tells the model the tool's name, what it
  does and which arguments it takes.

The `TOOLS` dictionary maps each tool name to its function, so the loop can look up
whichever tool the model asks for by name.

## Skills

A skill is a folder with a `SKILL.md` file that starts with YAML frontmatter:

```markdown
---
name: git-commit
description: Use when the user asks to commit changes. Covers checking what
  changed, staging the right files and writing the commit message.
---

# Committing changes

1. Run `git status` and `git diff` to see what changed.
...
```

[skills.py](skills.py) looks for skills in two places when the harness starts:

| Folder | Scope |
|---|---|
| `./.agents/skills/<name>/SKILL.md` | This project (run `agent.py` from the project folder) |
| `~/.agents/skills/<name>/SKILL.md` | Every project on your machine |

If both folders have a skill with the same name, the project one wins. Files with
missing or malformed frontmatter are skipped.

Skills use **progressive disclosure**:

1. Only each skill's `name` and `description` go into the system prompt, so having many
   skills costs few tokens.
2. When a task matches a description, the model calls `read_skill` with that name and
   gets the full instructions back as a tool result.
3. The model then follows those instructions using its other tools.

This repo ships one example, [.agents/skills/git-commit](.agents/skills/git-commit/SKILL.md),
which teaches the agent this repo's commit style. To add your own, create a new folder
under `.agents/skills/` with a `SKILL.md`, then restart the harness.

To see which skills are found, run:

```bash
python skills.py
```

## Browser (ego-browser)

The `browser` tool lets the agent drive a real Chromium browser through
[ego lite](https://lite.ego.app/)'s `ego-browser` CLI. It's optional: without
`ego-browser` on your `PATH`, the tool just returns an error to the model.

How it fits together:

1. The ego-browser skill (installed by ego lite in `~/.agents/skills/ego-browser`) shows
   up in the system prompt like any other skill.
2. Before its first browser task, the model runs `ego-browser skill` with `bash` to read
   the usage guide for the installed version.
3. It then writes JavaScript against ego-browser's API (`taskSpace()`, `page.goto()`,
   `page.snapshot()`, `page.click()`, ...) and sends it to the `browser` tool.

The tool runs `ego-browser nodejs` and passes the script on **stdin**, not through a
shell. On Windows, `bash` goes through cmd.exe, which has no heredoc and breaks
multi-line `-e` arguments, so stdin is the one form that works the same everywhere.
Each script times out after 180 seconds (`BROWSER_TIMEOUT` in [tools.py](tools.py)).

Things to know:

- Every call is a new Node process. Browser tabs and task spaces persist between calls,
  but JavaScript variables do not, so the model reuses its task space by id.
- The script doesn't run in your working directory and doesn't see your environment
  variables. Use absolute paths.
- Tool results are text only, so the model reads pages with `page.snapshot()`.
  Screenshots don't reach it yet.
- ego lite uses your real browser profile, including sites you're signed in to, and the
  harness doesn't ask before running a script. Watch what it does.
- Set `MAX_TOKENS` to around `4096` so long scripts aren't cut off.

## Project layout

| File | Purpose |
|---|---|
| [agent.py](agent.py) | Entry point. Reads your prompt and runs the agent loop |
| [llm.py](llm.py) | System prompt, retries, and the OpenRouter and Anthropic providers |
| [context.py](context.py) | The `<env>` reminder (time, git branch) sent with each request |
| [tools.py](tools.py) | Tool functions, their schemas and the `TOOLS` lookup table |
| [skills.py](skills.py) | Finds `SKILL.md` files, builds the skills list for the system prompt, and implements `read_skill` |
| [.agents/skills/](.agents/skills) | Project skills |
| [ui.py](ui.py) | Terminal UI: prompt, spinner, tool panels, Markdown replies, usage (built on `rich` and `prompt_toolkit`) |

## Requirements

- Python 3.13 or newer (see `pyproject.toml`)
- An API key for one of the two providers:
  - [OpenRouter](https://openrouter.ai/keys), for many models (including free ones) through
    one OpenAI-compatible API, or
  - [Anthropic](https://platform.claude.com/), to call Claude models directly. API usage
    needs credits in the Anthropic Console; a Claude.ai subscription doesn't include them.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project folder. For OpenRouter:

```env
PROVIDER=openrouter
BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=your-key-here
MODEL=openai/gpt-4o-mini
```

Or for Anthropic:

```env
PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key-here
MODEL=claude-opus-5-5
```

| Variable | Used by | Description |
|---|---|---|
| `PROVIDER` | Both | `openrouter` or `anthropic`. Defaults to `openrouter` |
| `MODEL` | Both | The model ID. OpenRouter: any ID from [its model list](https://openrouter.ai/models) that supports tool calling (required). Anthropic: e.g. `claude-opus-5-5`, `claude-sonnet-5-5` or `claude-haiku-5-5`; defaults to `claude-opus-5-5` |
| `BASE_URL` | OpenRouter | The OpenAI-compatible API endpoint: `https://openrouter.ai/api/v1` |
| `OPENROUTER_API_KEY` | OpenRouter | Your OpenRouter API key |
| `ANTHROPIC_API_KEY` | Anthropic | Your Anthropic API key |
| `EFFORT` | Anthropic | Optional. How hard Claude thinks: `low`, `medium`, `high`, `xhigh` or `max`. Unset uses the model's default |
| `MAX_TOKENS` | Both | Optional. Maximum length of each reply in tokens. Defaults to `1000` for OpenRouter and `16000` for Anthropic, where thinking counts towards it |
| `MAX_RETRIES` | Both | Optional. How many times to retry a failed API request (see [Retries](#retries)). Defaults to `5` |

`.env` is already listed in `.gitignore`, so your API key won't be committed.

## Usage

```bash
python agent.py
```

This opens an interactive session:

- **Prompt** with history (saved to `~/.dcode_history`), autosuggest from past prompts,
  and tab completion for slash commands.
- **Spinner** while the model is thinking.
- **Tool calls** shown as `● bash  ls`, with the output in a panel (long output is
  cut to 12 lines on screen; the model still gets all of it). Tool errors show in red.
- **Replies** rendered as Markdown, followed by that request's token usage.
- **Follow-ups**: the conversation carries on until you `/clear` or quit.

| Command | What it does |
|---|---|
| `/help` | List commands |
| `/clear` | Start a new conversation |
| `/usage` | Show token totals for the session |
| `/exit` | Quit (Ctrl+D also works) |

Press **Ctrl+C** while the agent is working to stop that turn. The interrupted turn is
removed from the history so the next request stays valid.

## How it works

### Calling the model

[llm.py](llm.py) has two **providers**, picked by `PROVIDER` in `.env`. They speak
different API formats, so each one owns the format of its messages, and the agent loop
only talks to them through the same five methods:

| Method | What it does |
|---|---|
| `new_conversation()` | An empty history (OpenRouter puts the system prompt in it) |
| `user_message(text)` | Your prompt as a history entry |
| `call(messages, reminder, on_retry)` | Sends the history and returns a `Reply` |
| `tool_results(results)` | Turns `(id, output, is_error)` tuples into history entries |
| `.model` / `.name` | Shown in the banner |

A `Reply` looks the same from either provider: `message` (appended to the history
as-is), `text`, `tool_calls` (each with `id`, `name` and JSON `arguments`), `usage`,
`truncated` (hit `MAX_TOKENS`) and `refused` (the model declined).

How the two differ:

| | `OpenRouterProvider` | `AnthropicProvider` |
|---|---|---|
| SDK and API | `openai`, Chat Completions | `anthropic`, Messages API |
| System prompt | First message in the history | Separate `system` parameter |
| Tool schemas | `TOOL_SCHEMAS` as written | Converted to `name` / `description` / `input_schema` |
| Model's tool calls | `message.tool_calls` | `tool_use` blocks in the reply's content |
| Tool results | One `role: "tool"` message per result | All results in one `user` message as `tool_result` blocks |
| `<env>` reminder | Sent at the end of each request, then dropped | Added to the latest user message and kept (see below) |
| Prompt caching | Whatever the model does automatically | Turned on with `cache_control` |

`usage` has the same four counts for both:

- `prompt_tokens`: tokens in the input (system prompt, history and tool results)
- `completion_tokens`: tokens in the model's reply
- `reasoning_tokens`: tokens spent on internal reasoning, when the model reports them
- `cached_tokens`: input tokens served from the prompt cache, when reported

#### Why Anthropic keeps the reminder

Current Claude models think before they answer, and their thinking blocks come back in
each reply. The harness must send those blocks back unchanged, and the API checks that
the history they were written after hasn't been edited since. A reminder that is sent
once and then dropped counts as an edit, so the Anthropic provider keeps each one in
the history instead. The history only ever grows, which also keeps it cacheable.

#### Refusals and fallbacks

On `claude-opus-5-5`, `claude-opus-5`, `claude-sonnet-5-5` and `claude-fable-5-1`, the
Anthropic provider turns on **server-side fallbacks** (`fallbacks="default"`). If the
model declines a request on safety grounds, the API reruns it on another model in the
same call instead of just stopping. If the whole chain declines, dcode says so. To turn
it off, empty `FALLBACK_MODELS` in [llm.py](llm.py).

### Retries

Some API errors go away if you wait: rate limits (`429`, common on `:free` models),
server errors (`5xx`), timeouts and dropped connections. `with_retries()` in
[llm.py](llm.py) catches these from either SDK and tries again, up to `MAX_RETRIES` times:

- If the server sends a `retry-after` header, it waits that long (capped at `MAX_WAIT`).
- Otherwise it backs off exponentially: 2s, 4s, 8s, then `MAX_WAIT` (8s) for each
  later try.
- Each wait is shown in the terminal, e.g. `↻ 429 from the API, retrying in 4s (2/5)`.
- Ctrl+C during a wait stops the turn as usual.

Other errors are not retried, because waiting won't fix them: a bad API key (`401`),
running out of credits (`402`) or a malformed request (`400`). Those are shown straight
away.

Both SDKs have their own short built-in retries. They're turned off
(`max_retries=0` on each client) so the two don't stack.

### The agent loop

[agent.py](agent.py) keeps a `messages` list that starts with
`provider.new_conversation()` and your prompt, then repeats:

1. Call `provider.call()` with the whole `messages` list and the `<env>` reminder from
   [context.py](context.py).
2. Append `reply.message` to `messages`, so the model's tool calls (and, for Claude, its
   thinking) stay in the history.
3. If the reply has no tool calls, stop.
4. Otherwise run each tool call: parse the JSON arguments and run
   `TOOLS[name](**args)`. Each result is an `(id, output, is_error)` tuple. The id
   links the result to the call that asked for it, and the API rejects the next request
   if a tool call has no matching result.
5. Append `provider.tool_results(results)` to `messages` and go back to step 1.

If a reply was cut off at `MAX_TOKENS` in the middle of a tool call, its arguments may
be incomplete. The loop doesn't run those calls, but still answers each one with an
error so the history stays valid.

Because the full history is sent on every turn, the model sees everything it has
already run and read, and can decide what to do next.

## Current limitations

- **No turn limit.** The loop runs until the model stops asking for tools. A model that
  keeps calling tools will keep the loop going and keep using tokens.
- **Commands run without confirmation.** `bash` runs whatever the model asks for with
  `shell=True`, including commands that change or delete files. Only use it in a folder
  you're happy for it to touch.
- **No command timeout for `bash`.** (`browser` has one.) A command that never exits, or waits for input, hangs the harness.
- **Tool errors aren't retried.** Tool errors (missing file, bad JSON arguments, unknown
  tool) are sent back to the model to deal with. API errors are retried only when
  waiting can help (see [Retries](#retries)).

## Roadmap

Done:

- [x] Send a prompt to a model through OpenRouter and report token usage (step 1)
- [x] Pass tool schemas to the API and handle `tool_calls` in the response
- [x] Run the requested tools and send their output back to the model
- [x] Loop until the model gives a final answer
- [x] Load skills from `SKILL.md` files on demand (step 3)
- [x] Drive a real browser with ego-browser

Next:

- [ ] Add a turn limit to the loop
- [ ] Ask for confirmation before running commands that could change or delete files
- [x] Catch tool errors so they go back to the model instead of crashing the harness
- [ ] Add a timeout to `bash`
- [x] Keep the conversation going across prompts
- [x] Polished terminal UI (`rich` + `prompt_toolkit`)
- [ ] Trim or summarize old history when it grows large
- [x] Handle errors and retry on rate limits
- [x] Call Anthropic directly as a second provider
- [ ] Log each step so runs can be debugged
