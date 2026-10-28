"""Late injection: a small block appended just before we send.

It goes at the END of the message list so the stable prefix in front of it stays cached.
"""

import hashlib
import os
import subprocess
from datetime import datetime

from pathlib import Path

LABELS = {"M": "modified", "D": "deleted", "A": "added", "??": "new"}

SEEN = {}

# notes the last time the agent read a particular file
def note_read(path):
    SEEN[path] = os.path.getmtime(path) 
    # updates the index of SEEN list at index "path" with current time

def git(command):
    result = subprocess.run(
        f"git {command}", shell=True, capture_output=True, text=True
    )
    return result.stdout.strip() or "(detached)"

# this function will be used in call_llm() to append messages
def reminder():
    """The block we append to the messages on every turn."""
    return {
        "role": "user",
        "content": (
            "<env>\n"
            f"time: {datetime.now():%Y-%m-%d %H:%M}\n"
            f"git branch: {git('branch --show-current').strip() or '(detached)'}\n"
            "</env>"
        ),
    }