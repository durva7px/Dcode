import json
import subprocess

# from . import history
# from . import sandbox

# tool function definition

def bash(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr

def read_file(path: str) -> str:
    """ Read a file and return it's contents """
    with open(path) as f:
        return f.read()

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
]

TOOLS = {
    "bash": bash,
    "read_file": read_file,
}