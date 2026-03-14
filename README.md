# personal-vault-task-mcp

A personal MCP server for querying and managing [Obsidian Tasks](https://obsidian.md/) directly from VS Code Copilot (or any MCP-compatible AI client).

Run it directly from GitHub with a single command — no manual install needed.

## Features

- **`list_tasks`** — Query tasks from your vault with flexible filters (status, tags, due date, folder)
- **`update_task`** — Mark done/undone, reschedule, add/remove tags, update description
- **`create_task`** — Add tasks to today's daily note, inbox, or any file

## Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) installed (`pip install uv` or follow the [uv install guide](https://docs.astral.sh/uv/getting-started/installation/))
- An [Obsidian](https://obsidian.md/) vault with the [Tasks plugin](https://obsidian-tasks-group.github.io/obsidian-tasks/)

### VS Code Copilot Config

Add this to `.vscode/mcp.json` in your project (or your VS Code user settings):

```json
{
  "servers": {
    "obsidian-tasks": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/sanjumsanthosh/personal-vault-task-mcp",
        "obsidian-tasks-mcp"
      ],
      "env": {
        "VAULT_PATH": "C:\\Users\\sanju\\Documents\\Notes\\Sanjay's Vault"
      }
    }
  }
}
```

### Local Development

```bash
# 1. Clone and enter the repo
git clone https://github.com/sanjumsanthosh/personal-vault-task-mcp
cd personal-vault-task-mcp

# 2. Install deps
pip install -e ".[dev]"

# 3. Set your vault path
cp .env.example .env
# Edit .env and set VAULT_PATH

# 4. Run locally
obsidian-tasks-mcp

# 5. Run tests
pytest
```

## Tool Reference

### `list_tasks`

```python
list_tasks(
    status="incomplete",     # "all" | "incomplete" | "complete"
    tags=[],                 # e.g. ["micro-mng-todo", "interesting-read"]
    due="all",               # "today" | "overdue" | "this_week" | "no_date" | "has_date" | "all"
    path_includes="",        # e.g. "Projects" — filter by folder
    path_excludes="Journal", # default excludes journal noise
    limit=50
)
```

### `update_task`

```python
update_task(
    file_path="Projects/work.md",
    line_number=14,
    operation="mark_done",  # See operations below
    value=""                # date string, tag name, or description text
)
```

**Operations:** `mark_done`, `mark_undone`, `add_due_date`, `reschedule`, `add_tag`, `remove_tag`, `update_description`

### `create_task`

```python
create_task(
    description="Review PR for auth module",
    tag="micro-mng-todo",
    due_date="2026-03-15",
    priority="high",          # "highest" | "high" | "medium" | "low" | "none"
    target="daily_note",      # "daily_note" | "inbox" | "file"
    file_path=""              # only needed when target="file"
)
```

## Task Format

This server reads and writes tasks in the [Obsidian Tasks plugin](https://obsidian-tasks-group.github.io/obsidian-tasks/) format:

```markdown
- [ ] Review PR for auth module 🔺 📅 2026-03-15 #micro-mng-todo
- [x] Deploy service ✅ 2026-03-14
```

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `VAULT_PATH` | Absolute path to your Obsidian vault | `C:\Users\sanju\Documents\Notes\Sanjay's Vault` |
