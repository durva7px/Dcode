---
name: git-commit
description: Use when the user asks to commit changes. Covers checking what
  changed, staging the right files and writing the commit message.
---

# Committing changes

1. Run `git status` and `git diff` to see what changed.
2. Stage only the files related to the task with `git add <file>`. Never use
   `git add -A` blindly, and never stage `.env` or other secrets.
3. Write the message in this repo's style: `<type>: <short summary>`, where
   type is one of `added`, `update`, `fix`, e.g. `added: skills loader`.
4. Commit with `git commit -m "<message>"`.
5. Run `git log --oneline -1` and tell the user the commit hash and message.
