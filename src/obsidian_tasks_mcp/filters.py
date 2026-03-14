"""Filter logic for Obsidian task lists."""

from datetime import date, timedelta


def apply_filters(
    tasks: list[dict],
    status: str = "incomplete",
    tags: list[str] | None = None,
    due: str = "all",
    path_includes: str = "",
    path_excludes: str = "Journal",
) -> list[dict]:
    """Apply multiple filters to a flat list of task dicts.

    Args:
        tasks:          All tasks to filter.
        status:         ``"all"``, ``"incomplete"``, or ``"complete"``.
        tags:           Only return tasks that contain *at least one* of these tags.
                        Empty list / None means no tag filter.
        due:            Due-date bucket: ``"today"``, ``"overdue"``, ``"this_week"``,
                        ``"no_date"``, ``"has_date"``, or ``"all"``.
        path_includes:  If non-empty, keep only tasks whose ``file_path`` contains
                        this substring (case-sensitive).
        path_excludes:  If non-empty, drop tasks whose ``file_path`` contains this
                        substring (case-sensitive).  Defaults to ``"Journal"``.

    Returns:
        Filtered list of task dicts (same objects, not copies).
    """
    if tags is None:
        tags = []

    result = tasks

    # --- status ---
    if status != "all":
        result = [t for t in result if t["status"] == status]

    # --- tags ---
    if tags:
        result = [t for t in result if any(tag in t["tags"] for tag in tags)]

    # --- due date ---
    if due != "all":
        today = date.today()
        result = _filter_by_due(result, due, today)

    # --- path filters ---
    if path_includes:
        result = [t for t in result if path_includes in t["file_path"]]

    if path_excludes:
        result = [t for t in result if path_excludes not in t["file_path"]]

    return result


def _filter_by_due(tasks: list[dict], due: str, today: date) -> list[dict]:
    """Return tasks matching the given due-date bucket."""
    today_iso = today.isoformat()
    end_of_week_iso = (today + timedelta(days=6)).isoformat()

    result = []
    for task in tasks:
        task_due = task.get("due_date", "")

        if due == "today":
            if task_due == today_iso:
                result.append(task)
        elif due == "overdue":
            if task_due and task_due < today_iso:
                result.append(task)
        elif due == "this_week":
            if task_due and today_iso <= task_due <= end_of_week_iso:
                result.append(task)
        elif due == "no_date":
            if not task_due:
                result.append(task)
        elif due == "has_date":
            if task_due:
                result.append(task)

    return result
