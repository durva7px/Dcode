import os
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich import box
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

# pink palette
PINK = "#ff79c6"
BLUSH = "#ffb3d9"
ROSE = "#d63384"
MAUVE = "#9e7a8f"
BORDER = "#6b3a55"
RED = "#ff4d6d"

THEME = Theme({
    "accent": f"bold {PINK}",
    "soft": BLUSH,
    "muted": MAUVE,
    "tool": f"bold {ROSE}",
    "badge": f"bold #1a0f15 on {PINK}",
    "error": f"bold {RED}",
    "markdown.code": f"bold {BLUSH} on #2b1622",
    "markdown.h1": f"bold {PINK}",
    "markdown.h2": f"bold {PINK}",
    "markdown.h3": f"bold {BLUSH}",
    "markdown.link": f"underline {BLUSH}",
    "markdown.item.bullet": f"bold {PINK}",
    "markdown.item.number": f"bold {PINK}",
    "markdown.block_quote": f"italic {MAUVE}",
    "rule.line": BORDER,
})

console = Console(theme=THEME, highlight=False)

COMMANDS = {
    "/help": "Show this help",
    "/clear": "Start a new conversation",
    "/usage": "Show token usage for this session",
    "/exit": "Quit dcode",
}

MAX_OUTPUT_LINES = 12

HISTORY_FILE = Path.home() / ".dcode_history"

PROMPT_STYLE = Style.from_dict({
    "prompt": f"{PINK} bold",
    "bottom-toolbar": f"noreverse {MAUVE}",
    "key": f"{BLUSH} bold",
    "completion-menu.completion": f"bg:#2b1622 {BLUSH}",
    "completion-menu.completion.current": f"bg:{PINK} #1a0f15 bold",
    "auto-suggestion": "#6b4a5c",
})

TOOL_ICONS = {
    "bash": "$",
    "read_file": "▤",
}


def make_prompt_session():
    toolbar = HTML(
        " <key>enter</key> send  ·  <key>/help</key> commands"
        "  ·  <key>ctrl+c</key> interrupt  ·  <key>ctrl+d</key> quit"
    )
    return PromptSession(
        history=FileHistory(str(HISTORY_FILE)),
        auto_suggest=AutoSuggestFromHistory(),
        completer=WordCompleter(list(COMMANDS), sentence=True),
        style=PROMPT_STYLE,
        bottom_toolbar=toolbar,
    )


def read_input(session):
    console.print()
    return session.prompt([("class:prompt", "❯ ")]).strip()


def banner(model):
    title = Text.assemble(("✿ ", "accent"), ("dcode", f"bold {PINK}"), ("  a coding agent harness", "muted"))

    info = Table.grid(padding=(0, 2))
    info.add_column(style="muted", justify="right")
    info.add_column(style="soft")
    info.add_row("model", model)
    info.add_row("cwd", os.getcwd())

    tip = Text.assemble(
        ("Ask for anything. Type ", "muted"), ("/help", "accent"), (" for commands.", "muted"),
    )
    console.print()
    console.print(Panel(
        Group(title, Text(), info, Text(), tip),
        box=box.ROUNDED,
        border_style=PINK,
        padding=(1, 3),
        expand=False,
    ))


def help_table():
    table = Table(
        box=box.ROUNDED,
        border_style=BORDER,
        header_style=f"bold {PINK}",
        title="✿ commands",
        title_style=f"bold {PINK}",
        title_justify="left",
        padding=(0, 2),
    )
    table.add_column("command")
    table.add_column("description")
    for name, desc in COMMANDS.items():
        table.add_row(Text(name, "accent"), Text(desc, "soft"))
    console.print()
    console.print(table)


def thinking():
    return console.status("[soft]thinking…[/]", spinner="dots12", spinner_style=PINK)


def agent_message(content):
    console.print()
    console.print(Text.assemble(("✿ ", "accent"), ("dcode", f"bold {PINK}")))
    console.print(Padding(Markdown(content, code_theme="dracula"), (0, 0, 0, 2)))


def _format_args(name, args):
    if name == "bash":
        return args.get("command", "")
    if name == "read_file":
        return args.get("path", "")
    return ", ".join(f"{k}={v!r}" for k, v in args.items())


def tool_call(name, args):
    icon = TOOL_ICONS.get(name, "⚙")
    console.print()
    console.print(Text.assemble(
        (f" {icon} {name} ", "badge"), ("  ", ""), (_format_args(name, args), "soft"),
    ))


def tool_result(result, error=False):
    lines = result.rstrip().splitlines() or ["(no output)"]
    shown = lines[:MAX_OUTPUT_LINES]
    body = Text("\n".join(shown), style="error" if error else "muted", no_wrap=False)
    hidden = len(lines) - MAX_OUTPUT_LINES
    console.print(Padding(Panel(
        body,
        box=box.ROUNDED,
        border_style=RED if error else BORDER,
        title=Text("✗ failed", "error") if error else None,
        title_align="left",
        subtitle=Text(f"+{hidden} more lines", f"italic {MAUVE}") if hidden > 0 else None,
        subtitle_align="right",
        padding=(0, 1),
    ), (0, 0, 0, 2)))


def _fmt(n):
    if n is None:
        return "–"
    return f"{n / 1000:.1f}k" if n >= 1000 else str(n)


def turn_usage(usage):
    console.print(
        Text.assemble(
            ("↑ ", "accent"), (_fmt(usage["prompt_tokens"]), "soft"), (" in  ", "muted"),
            ("↓ ", "accent"), (_fmt(usage["completion_tokens"]), "soft"), (" out  ", "muted"),
            ("◆ ", "accent"), (_fmt(usage["cached_tokens"]), "soft"), (" cached", "muted"),
        ),
        justify="right",
    )


def session_usage(totals):
    table = Table(
        box=box.ROUNDED,
        border_style=BORDER,
        show_header=False,
        title="✿ session usage",
        title_style=f"bold {PINK}",
        title_justify="left",
        padding=(0, 2),
    )
    table.add_column(style="muted")
    table.add_column(style=f"bold {BLUSH}", justify="right")
    table.add_row("requests", f"{totals['requests']:,}")
    table.add_row("input tokens", f"{totals['prompt_tokens']:,}")
    table.add_row("output tokens", f"{totals['completion_tokens']:,}")
    table.add_row("cached tokens", f"{totals['cached_tokens']:,}")
    console.print()
    console.print(table)


def info(text):
    console.print(Text.assemble(("  ✧ ", "accent"), (text, "muted")))


def error(text):
    console.print(Panel(
        Text(text, "error"),
        box=box.ROUNDED,
        title=Text("✗ error", "error"),
        title_align="left",
        border_style=RED,
        padding=(0, 1),
    ))


def divider():
    console.print(Rule(characters="┄", style=BORDER))
