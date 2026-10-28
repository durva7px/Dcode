import json

import ui
from llm import provider
from tools import TOOLS
from context import reminder


def new_conversation():
    return provider.new_conversation()


def run_tool(tool_call):
    """Run one tool call and return (result, is_error)."""
    name = tool_call.name
    try:
        args = json.loads(tool_call.arguments or "{}")
    except json.JSONDecodeError as e:
        ui.tool_call(name, {})
        result = f"Error: invalid JSON arguments: {e}"
        ui.tool_result(result, error=True)
        return result, True

    ui.tool_call(name, args)
    if name not in TOOLS:
        result = f"Error: unknown tool '{name}'"
        ui.tool_result(result, error=True)
        return result, True

    try:
        result = TOOLS[name](**args)
    except Exception as e:
        result = f"Error: {type(e).__name__}: {e}"
        ui.tool_result(result, error=True)
        return result, True

    ui.tool_result(result)
    return result, False

def run_turn(messages, totals):
    while True:
        with ui.thinking():
            reply = provider.call(messages, reminder()["content"], on_retry=ui.retrying)
        messages.append(reply.message)

        totals["requests"] += 1
        for key in ("prompt_tokens", "completion_tokens", "cached_tokens"):
            totals[key] += reply.usage[key] or 0

        if reply.text:
            ui.agent_message(reply.text)
        if reply.refused:
            ui.info("The model declined this request.")
        if reply.truncated:
            ui.info("The reply was cut off at MAX_TOKENS.")

        if not reply.tool_calls:
            ui.turn_usage(reply.usage)
            return

        results = []
        for tool_call in reply.tool_calls:
            if reply.truncated:
                # the call's arguments may be incomplete, so don't run it,
                # but still answer it so the history stays valid
                results.append((tool_call.id, "Error: the reply was cut off before this "
                                "tool call was complete, so it was not run.", True))
            else:
                results.append((tool_call.id, *run_tool(tool_call)))
        messages.extend(provider.tool_results(results))


def main():
    session = ui.make_prompt_session()
    messages = new_conversation()
    totals = {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0, "cached_tokens": 0}

    ui.banner(f"{provider.model}  ({provider.name})")

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
        messages.append(provider.user_message(user_input))
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
