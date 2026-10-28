import json

import ui
from llm import MODEL, SYSTEM_PROMPT, call_llm
from tools import TOOLS


def new_conversation():
    return [{"role": "system", "content": SYSTEM_PROMPT}]


def run_tool(tool_call):
    name = tool_call.function.name
    try:
        args = json.loads(tool_call.function.arguments or "{}")
    except json.JSONDecodeError as e:
        ui.tool_call(name, {})
        result = f"Error: invalid JSON arguments: {e}"
        ui.tool_result(result, error=True)
        return result

    ui.tool_call(name, args)
    if name not in TOOLS:
        result = f"Error: unknown tool '{name}'"
        ui.tool_result(result, error=True)
        return result

    try:
        result = TOOLS[name](**args)
    except Exception as e:
        result = f"Error: {type(e).__name__}: {e}"
        ui.tool_result(result, error=True)
        return result

    ui.tool_result(result)
    return result


def run_turn(messages, totals):
    while True:
        with ui.thinking():
            message, usage = call_llm(messages)
        messages.append(message.model_dump(exclude_none=True))

        totals["requests"] += 1
        for key in ("prompt_tokens", "completion_tokens", "cached_tokens"):
            totals[key] += usage[key] or 0

        if message.content:
            ui.agent_message(message.content)

        if not message.tool_calls:
            ui.turn_usage(usage)
            return

        for tool_call in message.tool_calls:
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": run_tool(tool_call),
            })


def main():
    session = ui.make_prompt_session()
    messages = new_conversation()
    totals = {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0, "cached_tokens": 0}

    ui.banner(MODEL)

    while True:
        try:
            user_input = ui.read_input(session)
        except KeyboardInterrupt:
            continue
        except EOFError:
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            command = user_input.split()[0]
            if command in ("/exit", "/quit"):
                break
            elif command == "/help":
                ui.help_table()
            elif command == "/clear":
                messages = new_conversation()
                ui.info("Started a new conversation.")
            elif command == "/usage":
                ui.session_usage(totals)
            else:
                ui.info(f"Unknown command {command}. Type /help for commands.")
            continue

        # roll back on failure so a half-finished turn (e.g. tool calls without results)
        # never ends up in the history the API sees next time
        checkpoint = len(messages)
        messages.append({"role": "user", "content": user_input})
        try:
            run_turn(messages, totals)
        except KeyboardInterrupt:
            del messages[checkpoint:]
            ui.info("Interrupted. That turn was discarded.")
        except Exception as e:
            del messages[checkpoint:]
            ui.error(f"{type(e).__name__}: {e}")

    ui.info("Bye!")


if __name__ == "__main__":
    main()
