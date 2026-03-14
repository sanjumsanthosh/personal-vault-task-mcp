"""Unit tests for obsidian_tasks_mcp.filters."""

from datetime import date, timedelta

import pytest

from obsidian_tasks_mcp.filters import apply_filters


# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

TODAY = date.today()
YESTERDAY = (TODAY - timedelta(days=1)).isoformat()
TOMORROW = (TODAY + timedelta(days=1)).isoformat()
IN_5_DAYS = (TODAY + timedelta(days=5)).isoformat()
IN_10_DAYS = (TODAY + timedelta(days=10)).isoformat()
TODAY_ISO = TODAY.isoformat()


SAMPLE_TASKS: list[dict] = [
    {
        "id": "Projects/work.md:5",
        "description": "Review end-to-end flow",
        "status": "incomplete",
        "tags": ["micro-mng-todo"],
        "due_date": TODAY_ISO,
        "priority": "highest",
        "file_path": "Projects/work.md",
        "line_number": 5,
    },
    {
        "id": "Projects/work.md:6",
        "description": "Update API documentation",
        "status": "incomplete",
        "tags": [],
        "due_date": IN_10_DAYS,
        "priority": "none",
        "file_path": "Projects/work.md",
        "line_number": 6,
    },
    {
        "id": "Projects/work.md:7",
        "description": "Set up CI/CD pipeline",
        "status": "complete",
        "tags": [],
        "due_date": "",
        "priority": "none",
        "file_path": "Projects/work.md",
        "line_number": 7,
    },
    {
        "id": "Journal/2026-03-14.md:5",
        "description": "Review morning emails",
        "status": "incomplete",
        "tags": ["micro-mng-todo"],
        "due_date": TODAY_ISO,
        "priority": "none",
        "file_path": "Journal/2026-03-14.md",
        "line_number": 5,
    },
    {
        "id": "Projects/work.md:8",
        "description": "Interesting article on distributed systems",
        "status": "incomplete",
        "tags": ["interesting-read"],
        "due_date": "",
        "priority": "none",
        "file_path": "Projects/work.md",
        "line_number": 8,
    },
    {
        "id": "Projects/work.md:9",
        "description": "Overdue task",
        "status": "incomplete",
        "tags": [],
        "due_date": YESTERDAY,
        "priority": "none",
        "file_path": "Projects/work.md",
        "line_number": 9,
    },
    {
        "id": "Projects/work.md:10",
        "description": "Task due in 5 days",
        "status": "incomplete",
        "tags": [],
        "due_date": IN_5_DAYS,
        "priority": "none",
        "file_path": "Projects/work.md",
        "line_number": 10,
    },
]


# ---------------------------------------------------------------------------
# Status filter
# ---------------------------------------------------------------------------


def test_filter_incomplete_default():
    result = apply_filters(SAMPLE_TASKS, status="incomplete", path_excludes="")
    assert all(t["status"] == "incomplete" for t in result)


def test_filter_complete():
    result = apply_filters(SAMPLE_TASKS, status="complete", path_excludes="")
    assert all(t["status"] == "complete" for t in result)
    assert len(result) == 1


def test_filter_all_status():
    result = apply_filters(SAMPLE_TASKS, status="all", path_excludes="")
    assert len(result) == len(SAMPLE_TASKS)


# ---------------------------------------------------------------------------
# Tag filter
# ---------------------------------------------------------------------------


def test_filter_by_single_tag():
    result = apply_filters(SAMPLE_TASKS, status="all", tags=["micro-mng-todo"], path_excludes="")
    assert all("micro-mng-todo" in t["tags"] for t in result)
    assert len(result) == 2


def test_filter_by_multiple_tags_any_match():
    result = apply_filters(
        SAMPLE_TASKS, status="all", tags=["micro-mng-todo", "interesting-read"], path_excludes=""
    )
    assert len(result) == 3  # 2 micro-mng-todo + 1 interesting-read


def test_filter_no_tags_returns_all():
    result = apply_filters(SAMPLE_TASKS, status="all", tags=[], path_excludes="")
    assert len(result) == len(SAMPLE_TASKS)


def test_filter_tags_none_equivalent_to_empty():
    result = apply_filters(SAMPLE_TASKS, status="all", tags=None, path_excludes="")
    assert len(result) == len(SAMPLE_TASKS)


# ---------------------------------------------------------------------------
# Due date filter
# ---------------------------------------------------------------------------


def test_filter_due_today():
    result = apply_filters(SAMPLE_TASKS, status="all", due="today", path_excludes="")
    assert all(t["due_date"] == TODAY_ISO for t in result)
    assert len(result) == 2  # two tasks due today


def test_filter_due_overdue():
    result = apply_filters(SAMPLE_TASKS, status="all", due="overdue", path_excludes="")
    assert all(t["due_date"] < TODAY_ISO for t in result)
    assert len(result) == 1


def test_filter_due_this_week():
    result = apply_filters(SAMPLE_TASKS, status="all", due="this_week", path_excludes="")
    # today + in_5_days both fall within 6-day window; in_10_days does not
    assert all(t["due_date"] >= TODAY_ISO for t in result)
    assert not any(t["due_date"] == IN_10_DAYS for t in result)


def test_filter_due_no_date():
    result = apply_filters(SAMPLE_TASKS, status="all", due="no_date", path_excludes="")
    assert all(t["due_date"] == "" for t in result)
    assert len(result) == 2  # CI/CD pipeline + interesting article


def test_filter_due_has_date():
    result = apply_filters(SAMPLE_TASKS, status="all", due="has_date", path_excludes="")
    assert all(t["due_date"] != "" for t in result)


def test_filter_due_all_no_change():
    result = apply_filters(SAMPLE_TASKS, status="all", due="all", path_excludes="")
    assert len(result) == len(SAMPLE_TASKS)


# ---------------------------------------------------------------------------
# Path filters
# ---------------------------------------------------------------------------


def test_filter_path_includes():
    result = apply_filters(SAMPLE_TASKS, status="all", path_includes="Projects", path_excludes="")
    assert all("Projects" in t["file_path"] for t in result)


def test_filter_path_excludes_journal():
    result = apply_filters(SAMPLE_TASKS, status="all", path_excludes="Journal")
    assert not any("Journal" in t["file_path"] for t in result)


def test_filter_path_excludes_empty_keeps_all():
    result = apply_filters(SAMPLE_TASKS, status="all", path_excludes="")
    assert len(result) == len(SAMPLE_TASKS)


def test_filter_path_includes_and_excludes_combined():
    result = apply_filters(
        SAMPLE_TASKS,
        status="all",
        path_includes="Projects",
        path_excludes="Journal",
    )
    assert all("Projects" in t["file_path"] for t in result)
    assert not any("Journal" in t["file_path"] for t in result)


# ---------------------------------------------------------------------------
# Default behaviour (mirrors server defaults)
# ---------------------------------------------------------------------------


def test_default_filters_exclude_journal_and_incomplete():
    # Simulates calling list_tasks with no args
    result = apply_filters(SAMPLE_TASKS)  # status="incomplete", path_excludes="Journal"
    assert all(t["status"] == "incomplete" for t in result)
    assert not any("Journal" in t["file_path"] for t in result)
