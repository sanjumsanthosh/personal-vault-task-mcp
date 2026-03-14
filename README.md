# personal-vault-task-mcp

A personal MCP server for querying and managing [Obsidian Tasks](https://obsidian.md/) directly from VS Code Copilot (or any MCP-compatible AI client).

Run it directly from GitHub with a single command — no manual install needed.

## Features

- **`list_tasks`** — Query tasks from your vault with flexible filters (status, tags, due date, folder)
- **`update_task`** — Mark done/undone, reschedule, add/remove tags, update description
- **`create_task`** — Add tasks to today's daily note, inbox, or any file
- **`get_daily_briefing`** — Get today's due tasks and all overdue incomplete tasks in one call
- **`get_task_stats`** — Counts grouped by status, file, tag, and priority
- **`delete_task`** — Remove a task line from a file (with optional dry-run preview)
- **`bulk_update_tasks`** — Apply the same operation to many tasks at once, selected by ID or filter
- **`search_tasks`** — Full-text search across descriptions, wikilinks, and tags with relevance ranking

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

### `get_daily_briefing`

```python
get_daily_briefing()
```

Returns today's due tasks and all overdue incomplete tasks. Unlike `list_tasks` and `search_tasks`, this tool searches across **all** files — including Journal files — so no tasks are missed.

**Response fields:** `date`, `today_count`, `today_tasks`, `overdue_count`, `overdue_tasks`

### `get_task_stats`

```python
get_task_stats()
```

Returns aggregate counts for every task in the vault.

**Response fields:** `total`, `by_status`, `by_file`, `by_tag`, `by_priority`

### `delete_task`

```python
delete_task(
    file_path="Projects/work.md",
    line_number=14,
    dry_run=False   # True = preview only, no changes written
)
```

Deletes a task line from a vault file. Use `dry_run=True` to preview the deletion before committing.

### `bulk_update_tasks`

```python
bulk_update_tasks(
    task_ids=["Projects/work.md:5", "Projects/work.md:10"],  # explicit IDs, or…
    filter_file="Projects/work.md",   # …use filters to select automatically
    filter_status="incomplete",
    filter_tag="tech-debt",
    operation="mark_done",            # same operations as update_task
    value="",
    dry_run=False
)
```

Applies the same operation to many tasks at once. Provide either explicit `task_ids` (formatted as `"file_path:line"`) or a combination of `filter_file`, `filter_status`, and `filter_tag`. Updates are applied bottom-up within each file to keep line numbers stable.

### `search_tasks`

```python
search_tasks(
    query="auth module",
    status="incomplete",       # "all" | "incomplete" | "complete"
    path_excludes="Journal",   # default excludes journal noise
    limit=30
)
```

Full-text search across task descriptions, wikilinks, and tags. Results are ranked by relevance:

| Score | Condition |
|-------|-----------|
| 100 | Exact phrase match |
| 70 | All query tokens present |
| 50 | Tag contains query text |
| ≤ 40 | Partial token match |

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
