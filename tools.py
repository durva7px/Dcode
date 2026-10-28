import json
import subprocess

from skills import read_skill
from context import note_read

# from . import history
# from . import sandbox

# tool function definition

def bash(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr

def read_file(path: str) -> str:
    """ Read a file and return it's contents """
    note_read(path)
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

BROWSER_TIMEOUT = 180

def browser(script: str) -> str:
    """ Run a script with ego-browser's Node runtime and return its output """
    # the script goes in on stdin, so no shell ever has to quote it
    try:
        result = subprocess.run(
            ["ego-browser", "nodejs"],
            input=script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=BROWSER_TIMEOUT,
        )
    except FileNotFoundError:
        return "Error: ego-browser is not installed or not on PATH"
    except subprocess.TimeoutExpired:
        return f"Error: browser script timed out after {BROWSER_TIMEOUT}s"
    return result.stdout + result.stderr

# tools schema

TOOL_SCHEMAS = [
  {
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
        },
    },
},

    {
        "type": "function",
        "function": {
            "name": "read_file", 
            "description": "Read the contents of a file and return.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file",
                    }
                },
                "required": ["path"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "read_skill",
            "description": "Load a skill's full instructions by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The skill name",
                    }
                },
                "required": ["name"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "browser",
            "description": (
                "Run a JavaScript (ESM) script with ego-browser's Node runtime to control a real browser. "
                "Before the first use, run `ego-browser skill` with the bash tool and follow that guide. "
                "Each call is a new process: reuse the same taskSpace by its id and page labels across calls. "
                "Use absolute paths for any files the script reads or writes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "The JavaScript to run",
                    }
                },
                "required": ["script"],
            },
        },
    },
]

TOOLS = {
    "bash": bash,
    "read_file": read_file,
    "read_skill": read_skill,
    "browser": browser,
}