# personal-vault-task-mcp

A personal MCP server for querying and managing [Obsidian Tasks](https://obsidian.md/) directly from VS Code Copilot (or any MCP-compatible AI client).

Run it directly from GitHub with a single command — no manual install needed.

## Features

- **`list_tasks`** — Query tasks with flexible filters; optional `group_by` returns pre-organised buckets; always reports `total_count` so truncation is never silent
- **`update_task`** — Mark done/undone, reschedule, add/remove tags, update description, set/clear a reminder
- **`create_task`** — Add tasks to today's daily note, inbox, or any file; supports the Reminder plugin `⏰` field
- **`get_daily_briefing`** — Get today's due tasks and all overdue incomplete tasks in one call
- **`get_task_summary`** — Pre-grouped, pre-counted task view (by file, tag, priority, or date) — no limit applied so counts are always accurate
- **`get_task_stats`** — Raw counts grouped by status, file, tag, and priority
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
    group_by="",             # "file" | "tag" | "priority" | "date" — omit for flat list
    limit=200
)
```

Always returns a **dict** (not a list) so `total_count` is always visible:

```json
// Without group_by
{ "tasks": [...], "total_count": 42, "returned_count": 42, "limit": 200 }

// With group_by="file"
{ "group_by": "file", "groups": { "Projects/work.md": [...] }, "total_count": 42, "returned_count": 42, "limit": 200 }
```

`group_by` date buckets: `overdue`, `today`, `this_week`, `future`, `no_date`.  
`group_by` tag: tasks with no tags appear under `"untagged"`.

### `update_task`

```python
update_task(
    file_path="Projects/work.md",
    line_number=14,
    operation="mark_done",  # See operations below
    value=""                # date string, tag name, description text, or reminder datetime
)
```

**Operations:** `mark_done`, `mark_undone`, `add_due_date`, `reschedule`, `add_tag`, `remove_tag`, `update_description`, `add_reminder`, `remove_reminder`

| Operation | `value` |
|-----------|---------|
| `mark_done` | _(ignored)_ |
| `mark_undone` | _(ignored)_ |
| `add_due_date` / `reschedule` | `YYYY-MM-DD` |
| `add_tag` / `remove_tag` | tag name (with or without `#`) |
| `update_description` | replacement text |
| `add_reminder` | `YYYY-MM-DD` or `YYYY-MM-DD HH:mm` |
| `remove_reminder` | _(ignored)_ |

### `create_task`

```python
create_task(
    description="Review PR for auth module",
    tag="micro-mng-todo",
    due_date="2026-03-15",
    reminder_time="2026-03-15 09:00",  # ⏰ YYYY-MM-DD or YYYY-MM-DD HH:mm (optional)
    priority="high",                    # "highest" | "high" | "medium" | "low" | "none"
    target="daily_note",                # "daily_note" | "inbox" | "file"
    file_path=""                        # only needed when target="file"
)
```

When `reminder_time` is provided the task line is written with the `⏰` Reminder plugin field placed immediately before `📅`:

```markdown
- [ ] Review PR for auth module 🔺 ⏰ 2026-03-15 09:00 📅 2026-03-15 #micro-mng-todo
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

### `get_task_summary`

```python
get_task_summary(
    status="incomplete",     # "all" | "incomplete" | "complete"
    group_by="file",         # "file" | "tag" | "priority" | "date"
    tags=[],                 # optional tag pre-filter
    due="all",               # optional due-date pre-filter
    path_includes="",
    path_excludes="Journal"
)
```

Purpose-built for the **"show me all my tasks organised"** use case. Unlike `list_tasks` no item limit is applied — counts are always accurate. Each group contains a `count` and the full `tasks` list:

```json
{
  "group_by": "file",
  "total_count": 42,
  "group_count": 5,
  "groups": {
    "Projects/work.md":  { "count": 12, "tasks": [...] },
    "Projects/mobile.md": { "count": 7,  "tasks": [...] }
  }
}
```

`group_by` date buckets: `overdue`, `today`, `this_week`, `future`, `no_date`.  
`group_by` tag: tasks with no tags appear under `"untagged"`.

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

**Operations:** `mark_done`, `mark_undone`, `add_due_date`, `reschedule`, `add_tag`, `remove_tag`, `update_description`, `add_reminder`, `remove_reminder`

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

### Reminder plugin (`⏰`) support

The server also handles the [Obsidian Reminder plugin](https://github.com/uphy/obsidian-reminder) `⏰` field. The reminder datetime is placed **between the priority and the due date** — the Reminder plugin requires that nothing appear between `⏰` and `📅`:

```markdown
- [ ] Review PR for auth module 🔺 ⏰ 2026-03-15 09:00 📅 2026-03-15 #micro-mng-todo
```

Supported formats:

| Format | Meaning |
|--------|---------|
| `⏰ YYYY-MM-DD` | Reminder on that date at the plugin's default time |
| `⏰ YYYY-MM-DD HH:mm` | Reminder at a specific time |

Every parsed task includes a `reminder_time` field (`""` when absent). Use `add_reminder` / `remove_reminder` in `update_task` or `bulk_update_tasks` to manage reminders on existing tasks.

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `VAULT_PATH` | Absolute path to your Obsidian vault | `C:\Users\sanju\Documents\Notes\Sanjay's Vault` |
