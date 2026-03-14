"""FastMCP server exposing three Obsidian Tasks tools: list_tasks, update_task, create_task."""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import FastMCP

from obsidian_tasks_mcp.filters import apply_filters
from obsidian_tasks_mcp.vault import VaultManager

load_dotenv()

VAULT_PATH = Path(os.environ.get("VAULT_PATH", ""))
vault = VaultManager(VAULT_PATH)
mcp = FastMCP("obsidian-tasks-mcp")


@mcp.tool()
def list_tasks(
    status: str = "incomplete",
    tags: list[str] = [],
    due: str = "all",
    path_includes: str = "",
    path_excludes: str = "Journal",
    limit: int = 50,
) -> list[dict]:
    """List tasks from your Obsidian vault with filters.

    Args:
        status:        Filter by completion: "all", "incomplete", or "complete".
        tags:          Only tasks that have at least one of these tags.
        due:           Due-date filter: "today", "overdue", "this_week",
                       "no_date", "has_date", or "all".
        path_includes: Keep only tasks whose file path contains this substring.
        path_excludes: Drop tasks whose file path contains this substring
                       (defaults to "Journal" to hide daily-note noise).
        limit:         Maximum number of tasks to return.
    """
    tasks = vault.get_all_tasks()
    return apply_filters(tasks, status, tags, due, path_includes, path_excludes)[:limit]


@mcp.tool()
def update_task(
    file_path: str, line_number: int, operation: str, value: str = ""
) -> dict:
    """Update a task in the vault — mark done, reschedule, add tag, etc.

    Args:
        file_path:   Vault-relative path, e.g. "Projects/work.md".
        line_number: 1-based line number as returned by list_tasks.
        operation:   One of: mark_done, mark_undone, add_due_date, reschedule,
                     add_tag, remove_tag, update_description.
        value:       Depends on the operation: a date string for
                     add_due_date/reschedule, a tag name for add_tag/remove_tag,
                     or free text for update_description.
    """
    return vault.update_task(file_path, line_number, operation, value)


@mcp.tool()
def create_task(
    description: str,
    tag: str = "",
    due_date: str = "",
    priority: str = "none",
    target: str = "daily_note",
    file_path: str = "",
) -> dict:
    """Create a new task and append it to a file in your vault.

    Args:
        description: The task text.
        tag:         Optional inline tag (e.g. "micro-mng-todo").
        due_date:    Optional due date in YYYY-MM-DD format.
        priority:    "highest", "high", "medium", "low", or "none".
        target:      Where to write the task — "daily_note", "inbox", or "file".
        file_path:   Required when target="file"; vault-relative path.
    """
    return vault.create_task(description, tag, due_date, priority, target, file_path)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
