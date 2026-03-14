"""FastMCP server exposing Obsidian Tasks tools: list_tasks, get_daily_briefing,
get_task_stats, get_task_summary, create_task, update_task, delete_task,
bulk_update_tasks, search_tasks."""

import os
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import FastMCP

from obsidian_tasks_mcp.filters import apply_filters
from obsidian_tasks_mcp.vault import VaultManager

load_dotenv()

VAULT_PATH = Path(os.environ.get("VAULT_PATH", ""))
vault = VaultManager(VAULT_PATH)
mcp = FastMCP("obsidian-tasks-mcp")


# ---------------------------------------------------------------------------
# Grouping helper (module-level so it can be tested independently)
# ---------------------------------------------------------------------------


def _group_tasks(tasks: list[dict], group_by: str) -> dict[str, list[dict]]:
    """Return *tasks* arranged into named buckets according to *group_by*.

    Supported group_by values:
        "file"      — bucket key is the vault-relative file path
        "tag"       — each task may appear in multiple buckets (one per tag);
                      tasks without tags appear under "untagged"
        "priority"  — bucket key is the priority string (highest/high/…/none)
        "date"      — bucket key is one of: overdue, today, this_week, future,
                      no_date
    """
    today = date.today()
    today_iso = today.isoformat()
    week_end_iso = (today + timedelta(days=6)).isoformat()

    groups: dict[str, list[dict]] = defaultdict(list)

    for task in tasks:
        if group_by == "file":
            groups[task["file_path"]].append(task)

        elif group_by == "tag":
            task_tags = task.get("tags", [])
            if task_tags:
                for tag in task_tags:
                    groups[tag].append(task)
            else:
                groups["untagged"].append(task)

        elif group_by == "priority":
            groups[task.get("priority", "none")].append(task)

        elif group_by == "date":
            due = task.get("due_date", "")
            if not due:
                groups["no_date"].append(task)
            elif due < today_iso:
                groups["overdue"].append(task)
            elif due == today_iso:
                groups["today"].append(task)
            elif due <= week_end_iso:
                groups["this_week"].append(task)
            else:
                groups["future"].append(task)

        else:
            raise ValueError(
                f"Unknown group_by value: {group_by!r}. "
                "Use 'file', 'tag', 'priority', or 'date'."
            )

    return dict(groups)


@mcp.tool()
def list_tasks(
    status: str = "incomplete",
    tags: list[str] = [],
    due: str = "all",
    path_includes: str = "",
    path_excludes: str = "Journal",
    group_by: str = "",
    limit: int = 200,
) -> dict:
    """List tasks from your Obsidian vault with filters.

    Always returns a dict so that ``total_count`` is visible alongside results —
    this prevents silent truncation (the AI knows when it's seeing a partial list).

    Args:
        status:        Filter by completion: "all", "incomplete", or "complete".
        tags:          Only tasks that have at least one of these tags.
        due:           Due-date filter: "today", "overdue", "this_week",
                       "no_date", "has_date", or "all".
        path_includes: Keep only tasks whose file path contains this substring.
        path_excludes: Drop tasks whose file path contains this substring
                       (defaults to "Journal" to hide daily-note noise).
        group_by:      When set, tasks are returned pre-grouped under a "groups"
                       key instead of a flat "tasks" list.  Supported values:
                       "file", "tag", "priority", "date".
        limit:         Maximum number of tasks to return (applied before grouping).
    """
    tasks = vault.get_all_tasks()
    filtered = apply_filters(tasks, status, tags, due, path_includes, path_excludes)
    total_count = len(filtered)
    limited = filtered[:limit]

    if group_by:
        groups = _group_tasks(limited, group_by)
        return {
            "group_by": group_by,
            "groups": groups,
            "total_count": total_count,
            "returned_count": len(limited),
            "limit": limit,
        }

    return {
        "tasks": limited,
        "total_count": total_count,
        "returned_count": len(limited),
        "limit": limit,
    }


@mcp.tool()
def update_task(
    file_path: str, line_number: int, operation: str, value: str = ""
) -> dict:
    """Update a task in the vault — mark done, reschedule, add reminder, etc.

    Args:
        file_path:   Vault-relative path, e.g. "Projects/work.md".
        line_number: 1-based line number as returned by list_tasks.
        operation:   One of: mark_done, mark_undone, add_due_date, reschedule,
                     add_tag, remove_tag, update_description,
                     add_reminder, remove_reminder.
        value:       Depends on the operation: a date string for
                     add_due_date/reschedule, a tag name for add_tag/remove_tag,
                     free text for update_description, or a reminder datetime
                     (YYYY-MM-DD or YYYY-MM-DD HH:mm) for add_reminder.
    """
    return vault.update_task(file_path, line_number, operation, value)


@mcp.tool()
def create_task(
    description: str,
    tag: str = "",
    due_date: str = "",
    reminder_time: str = "",
    priority: str = "none",
    target: str = "daily_note",
    file_path: str = "",
) -> dict:
    """Create a new task and append it to a file in your vault.

    Args:
        description:   The task text.
        tag:           Optional inline tag (e.g. "micro-mng-todo").
        due_date:      Optional due date in YYYY-MM-DD format.
        reminder_time: Optional reminder datetime for the Reminder plugin
                       (e.g. "2026-03-15" or "2026-03-15 09:00").  Written as
                       ⏰ YYYY-MM-DD HH:mm immediately before 📅 in the task line.
        priority:      "highest", "high", "medium", "low", or "none".
        target:        Where to write the task — "daily_note", "inbox", or "file".
        file_path:     Required when target="file"; vault-relative path.
    """
    return vault.create_task(description, tag, due_date, reminder_time, priority, target, file_path)


@mcp.tool()
def get_daily_briefing() -> dict:
    """Return a daily briefing: today's due tasks and overdue incomplete tasks.

    Includes tasks from all files (Journal and non-Journal) so nothing is missed.
    """
    tasks = vault.get_all_tasks()
    today_iso = date.today().isoformat()

    today_tasks = apply_filters(tasks, "incomplete", [], "today", "", "")
    overdue_tasks = apply_filters(tasks, "incomplete", [], "overdue", "", "")

    return {
        "date": today_iso,
        "today_count": len(today_tasks),
        "overdue_count": len(overdue_tasks),
        "today_tasks": today_tasks,
        "overdue_tasks": overdue_tasks,
    }


@mcp.tool()
def get_task_summary(
    status: str = "incomplete",
    group_by: str = "file",
    tags: list[str] = [],
    due: str = "all",
    path_includes: str = "",
    path_excludes: str = "Journal",
) -> dict:
    """Return a structured summary of tasks, pre-grouped and counted server-side.

    This tool is purpose-built for the "show me all my tasks organised" use case.
    Unlike list_tasks it always returns grouped output — no limit is applied so
    counts are always accurate.

    Args:
        status:        Filter by completion: "all", "incomplete", or "complete".
        group_by:      How to organise tasks: "file", "tag", "priority", or "date".
        tags:          Only tasks that have at least one of these tags.
        due:           Due-date filter: "today", "overdue", "this_week",
                       "no_date", "has_date", or "all".
        path_includes: Keep only tasks whose file path contains this substring.
        path_excludes: Drop tasks whose file path contains this substring
                       (defaults to "Journal" to hide daily-note noise).
    """
    tasks = vault.get_all_tasks()
    filtered = apply_filters(tasks, status, tags, due, path_includes, path_excludes)
    groups = _group_tasks(filtered, group_by)

    group_summaries = {
        key: {"count": len(group_tasks), "tasks": group_tasks}
        for key, group_tasks in groups.items()
    }

    return {
        "group_by": group_by,
        "total_count": len(filtered),
        "group_count": len(groups),
        "groups": group_summaries,
    }


@mcp.tool()
def get_task_stats() -> dict:
    """Return statistics about all tasks in the vault.

    Returns counts grouped by status, file, tag, and priority.
    """
    tasks = vault.get_all_tasks()

    status_counts = dict(Counter(t["status"] for t in tasks))

    file_counts: dict[str, int] = {}
    for t in tasks:
        fp = t["file_path"]
        file_counts[fp] = file_counts.get(fp, 0) + 1

    tag_counts: dict[str, int] = {}
    for t in tasks:
        for tag in t.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    priority_counts = dict(Counter(t.get("priority", "none") for t in tasks))

    return {
        "total": len(tasks),
        "by_status": status_counts,
        "by_file": file_counts,
        "by_tag": tag_counts,
        "by_priority": priority_counts,
    }


@mcp.tool()
def delete_task(file_path: str, line_number: int, dry_run: bool = False) -> dict:
    """Delete a task line from a vault file.

    Args:
        file_path:   Vault-relative path, e.g. "Projects/work.md".
        line_number: 1-based line number as returned by list_tasks.
        dry_run:     When True, return a preview of what would be deleted
                     without making any changes.
    """
    return vault.delete_task(file_path, line_number, dry_run)


# ---------------------------------------------------------------------------
# Search helpers (module-level so they can be tested independently)
# ---------------------------------------------------------------------------


def _score_match(text: str, query: str) -> int:
    """Score how well *query* matches *text*.

    Returns 100 for an exact phrase match, 70 if all tokens are present,
    a partial score (≤40) if some tokens match, or 0 for no match.
    """
    text_lower = text.lower()
    query_lower = query.lower()
    tokens = query_lower.split()

    if query_lower in text_lower:
        return 100
    if all(t in text_lower for t in tokens):
        return 70
    matched = sum(1 for t in tokens if t in text_lower)
    if matched > 0:
        return int((matched / len(tokens)) * 40)
    return 0


def _matches_query(task: dict, query: str) -> tuple[bool, int]:
    """Return (matched, score) for *task* against *query*.

    Searches the description, wikilinks, and tags.
    """
    score = _score_match(task.get("description", ""), query)

    for wl in task.get("wikilinks", []):
        score = max(score, _score_match(wl, query))

    for tag in task.get("tags", []):
        if query.lower() in tag.lower():
            score = max(score, 50)

    return score > 0, score


@mcp.tool()
def bulk_update_tasks(
    task_ids: list[str] | None = None,
    filter_file: str = "",
    filter_status: str = "incomplete",
    filter_tag: str = "",
    operation: str = "mark_done",
    value: str = "",
    dry_run: bool = False,
) -> dict:
    """Apply the same update operation to multiple tasks at once.

    Either provide explicit *task_ids* (e.g. from a previous list_tasks call),
    or use the *filter_* parameters to select tasks automatically.

    Args:
        task_ids:       Explicit list of task IDs in "file_path:line" format.
        filter_file:    Vault-relative file path substring to restrict scope
                        (required when task_ids is not provided).
        filter_status:  Status filter for auto-selection: "incomplete", "complete",
                        or "all".
        filter_tag:     Tag filter for auto-selection (optional).
        operation:      One of: mark_done, mark_undone, add_due_date, reschedule,
                        add_tag, remove_tag, update_description,
                        add_reminder, remove_reminder.
        value:          Argument for the operation (e.g. a date, tag name, or
                        reminder datetime YYYY-MM-DD HH:mm).
        dry_run:        When True, return a preview without writing changes.
    """
    resolved_ids = list(task_ids) if task_ids else []

    if not resolved_ids:
        if not filter_file:
            return {"error": "Provide either task_ids or filter_file for safety"}
        all_tasks = vault.get_all_tasks()
        tag_list = [filter_tag] if filter_tag else []
        filtered = apply_filters(all_tasks, filter_status, tag_list, "all", filter_file, "")
        resolved_ids = [t["id"] for t in filtered]

    if not resolved_ids:
        return {"message": "No tasks matched — nothing to update"}

    return vault.bulk_update_tasks(resolved_ids, operation, value, dry_run)


@mcp.tool()
def search_tasks(
    query: str,
    status: str = "incomplete",
    path_excludes: str = "Journal",
    limit: int = 30,
) -> list[dict]:
    """Search tasks by description text, wikilinks, or tags.

    Returns results ranked by relevance (exact phrase > all tokens > partial match).

    Args:
        query:         Search text (minimum 2 characters).
        status:        Filter by completion: "all", "incomplete", or "complete".
        path_excludes: Drop tasks whose file path contains this substring
                       (defaults to "Journal" to hide daily-note noise).
        limit:         Maximum number of results to return.
    """
    if len(query.strip()) < 2:
        return [{"error": "Query too short — minimum 2 characters"}]

    all_tasks = vault.get_all_tasks()
    filtered = apply_filters(all_tasks, status, [], "all", "", path_excludes)

    scored = []
    for task in filtered:
        matched, score = _matches_query(task, query)
        if matched:
            scored.append({**task, "_score": score})

    scored.sort(key=lambda t: (-t["_score"], t["file_path"]))

    return [{k: v for k, v in t.items() if k != "_score"} for t in scored[:limit]]


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
