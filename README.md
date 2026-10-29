# dcode: build a coding agent harness from scratch

dcode is a terminal coding agent built one stage at a time. Each stage adds one idea on
top of the last, from a single API call to an agent that runs tools in a loop, loads
skills, drives a browser and talks to more than one model provider.

Every stage lives on its own branch with its own code and README, so you can read,
run and compare them separately. This `main` branch always holds the code of the
**latest stage** (currently [stage 3](#stage-3-skills-a-browser-and-a-second-provider)),
with this overview as its README.

<img width="902" height="622" alt="dcode running in a terminal" src="https://github.com/user-attachments/assets/f42ea1c4-0011-4277-abbf-0381c8739cc7" />

## Stages

| Stage | Branch | What it adds | README |
|---|---|---|---|
| 1 | [`stage-01`](https://github.com/durva7px/Dcode/tree/stage-01) | One prompt to a model through OpenRouter, with token usage | [Stage 1 README](https://github.com/durva7px/Dcode/blob/stage-01/README.md) |
| 2 | [`stage-02`](https://github.com/durva7px/Dcode/tree/stage-02) | Tools, the agent loop, and an interactive terminal UI | [Stage 2 README](https://github.com/durva7px/Dcode/blob/stage-02/README.md) |
| 3 | [`stage-03`](https://github.com/durva7px/Dcode/tree/stage-03) | Skills, a browser tool, Anthropic as a second provider, retries | [Stage 3 README](https://github.com/durva7px/Dcode/blob/stage-03/README.md) |

### Stage 1: a basic chat call

A single script ([llm.py](https://github.com/durva7px/Dcode/blob/stage-01/llm.py)) that
sends one prompt to a model through [OpenRouter](https://openrouter.ai/), prints the
reply and reports the tokens used. There's no loop yet: one request, then it exits.

You'll learn: the Chat Completions request format, system prompts, and reading token
usage (including reasoning and cached tokens).

### Stage 2: tool calls and an agent loop

The model gets two tools, `bash` and `read_file`. The harness runs whatever tools the
model asks for, sends the results back and keeps looping until the model answers. The
conversation carries on across prompts in an interactive terminal UI built on `rich`
and `prompt_toolkit`, with `/help`, `/clear`, `/usage` and `/exit`.

You'll learn: tool schemas, `tool_calls` and `tool_call_id`, the agent loop, sending
tool errors back to the model, and keeping the history valid when a turn is interrupted.

### Stage 3: skills, a browser and a second provider

- **Skills**: reusable instructions in `SKILL.md` files. Only their names and
  descriptions go into the system prompt; the model loads the full text with a
  `read_skill` tool when a task needs it.
- **Browser**: a `browser` tool that drives a real Chromium browser through
  [ego-browser](https://lite.ego.app/).
- **Anthropic provider**: call Claude directly with your own Anthropic key, or keep using
  any model on OpenRouter. Picked with `PROVIDER` in `.env`.
- **Retries**: rate limits and server errors are retried with backoff.
- **Environment reminder**: the current time and git branch are sent with each request.

You'll learn: progressive disclosure, hiding two different API formats behind one
interface, prompt caching, and why an agent's history should only ever grow.

## Getting a stage

**Clone just one stage:**

```bash
git clone -b stage-02 --single-branch https://github.com/durva7px/Dcode.git dcode-stage-02
```

**Clone everything and switch between stages:**

```bash
git clone https://github.com/durva7px/Dcode.git
cd Dcode
git switch stage-01
```

**See what a stage changed** compared with the one before it:

```bash
git diff origin/stage-01 origin/stage-02 -- . ":!README.md"
```

or on GitHub, for example
[stage-02...stage-03](https://github.com/durva7px/Dcode/compare/stage-02...stage-03).

Each stage's README has its own requirements, setup and usage, so follow the README on
the branch you're on.

## Quick start (latest stage)

```bash
git clone https://github.com/durva7px/Dcode.git
cd Dcode
uv sync                  # or: python -m venv .venv, activate it, pip install -r requirements.txt
```

Create a `.env` file with your provider and key, for example:

```env
PROVIDER=openrouter
BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=your-key-here
MODEL=openai/gpt-4o-mini
```

Then run `python agent.py` (or `uv run agent.py`) from the project folder. For the
Anthropic setup and every other option, see the
[Stage 3 README](https://github.com/durva7px/Dcode/blob/stage-03/README.md#setup).

## How the branches work

- Each `stage-NN` branch is a finished stage. Its README documents that stage only.
- `main` has the same code as the latest stage, but its own README: this overview.
- When a new stage is ready, it's merged into `main`. The stage's code comes across;
  its README doesn't (see below).

### Adding a new stage (for maintainers)

1. Branch the new stage from the latest one, build it and write its README:

   ```bash
   git switch -c stage-04 stage-03
   ```

2. Merge it into `main` **locally**:

   ```bash
   git switch main
   git merge stage-04
   ```

3. Add the new stage to the [Stages](#stages) table and sections above, and update
   "currently stage N" in the intro.

`main` keeps its own README through [.gitattributes](.gitattributes), which marks
`README.md` with `merge=ours`. For that to work, each clone needs this setting once:

```bash
git config merge.ours.driver true
```

Two things to know:

- Merge on your machine, not with a GitHub pull request. GitHub doesn't run custom merge
  drivers, so a pull request would show a README conflict instead.
- Without the setting, git merges `README.md` like any other file, which usually means a
  conflict. If a merge ever brings a stage's README into `main`, restore this one with
  `git checkout HEAD~1 -- README.md` and commit.
