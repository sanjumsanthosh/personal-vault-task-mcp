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
        "status_char": " ",
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
        "status_char": " ",
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
        "status_char": "x",
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
        "status_char": " ",
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
        "status_char": " ",
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
        "status_char": " ",
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
        "status_char": " ",
        "tags": [],
        "due_date": IN_5_DAYS,
        "priority": "none",
        "file_path": "Projects/work.md",
        "line_number": 10,
    },
    {
        "id": "Projects/work.md:11",
        "description": "Working on auth refactor",
        "status": "incomplete",
        "status_char": "d",
        "tags": ["tech-debt"],
        "due_date": "",
        "priority": "none",
        "file_path": "Projects/work.md",
        "line_number": 11,
    },
    {
        "id": "Projects/work.md:12",
        "description": "Blocked by external team",
        "status": "incomplete",
        "status_char": "!",
        "tags": [],
        "due_date": "",
        "priority": "none",
        "file_path": "Projects/work.md",
        "line_number": 12,
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
    no_date_descriptions = {t["description"] for t in result}
    assert "Set up CI/CD pipeline" in no_date_descriptions
    assert "Interesting article on distributed systems" in no_date_descriptions
    assert "Working on auth refactor" in no_date_descriptions
    assert "Blocked by external team" in no_date_descriptions


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


# ---------------------------------------------------------------------------
# due_from / due_to range filters
# ---------------------------------------------------------------------------


def test_filter_due_from_excludes_earlier_and_no_date():
    result = apply_filters(SAMPLE_TASKS, status="all", due_from=TOMORROW, path_excludes="")
    # Only tasks with due_date >= TOMORROW
    assert all(t["due_date"] >= TOMORROW for t in result)
    assert all(t["due_date"] != "" for t in result)


def test_filter_due_to_excludes_later_and_no_date():
    result = apply_filters(SAMPLE_TASKS, status="all", due_to=YESTERDAY, path_excludes="")
    # Only tasks with due_date <= YESTERDAY
    assert all(t["due_date"] <= YESTERDAY for t in result)
    assert all(t["due_date"] != "" for t in result)


def test_filter_due_from_and_due_to_range():
    result = apply_filters(
        SAMPLE_TASKS,
        status="all",
        due_from=YESTERDAY,
        due_to=IN_5_DAYS,
        path_excludes="",
    )
    # Only tasks with due_date in [YESTERDAY, IN_5_DAYS]
    assert all(t["due_date"] >= YESTERDAY and t["due_date"] <= IN_5_DAYS for t in result)
    assert all(t["due_date"] != "" for t in result)


def test_filter_due_from_equal_boundary_included():
    result = apply_filters(SAMPLE_TASKS, status="all", due_from=TODAY_ISO, path_excludes="")
    assert all(t["due_date"] >= TODAY_ISO for t in result)
    today_tasks = [t for t in result if t["due_date"] == TODAY_ISO]
    assert len(today_tasks) == 2  # two tasks due today


def test_filter_due_to_equal_boundary_included():
    result = apply_filters(SAMPLE_TASKS, status="all", due_to=TODAY_ISO, path_excludes="")
    assert all(t["due_date"] <= TODAY_ISO for t in result)


def test_filter_due_from_no_match_returns_empty():
    far_future = (TODAY + timedelta(days=9999)).isoformat()
    result = apply_filters(SAMPLE_TASKS, status="all", due_from=far_future, path_excludes="")
    assert result == []


def test_filter_due_range_combined_with_status():
    result = apply_filters(
        SAMPLE_TASKS,
        status="incomplete",
        due_from=TODAY_ISO,
        due_to=IN_5_DAYS,
        path_excludes="",
    )
    assert all(t["status"] == "incomplete" for t in result)
    assert all(TODAY_ISO <= t["due_date"] <= IN_5_DAYS for t in result)


# ---------------------------------------------------------------------------
# status_chars filter
# ---------------------------------------------------------------------------


def test_filter_status_chars_doing():
    result = apply_filters(SAMPLE_TASKS, status="all", path_excludes="", status_chars=["d"])
    assert len(result) == 1
    assert result[0]["description"] == "Working on auth refactor"
    assert all(t["status_char"] == "d" for t in result)


def test_filter_status_chars_blocked():
    result = apply_filters(SAMPLE_TASKS, status="all", path_excludes="", status_chars=["!"])
    assert len(result) == 1
    assert result[0]["description"] == "Blocked by external team"


def test_filter_status_chars_multiple_values():
    result = apply_filters(SAMPLE_TASKS, status="all", path_excludes="", status_chars=["d", "!"])
    assert len(result) == 2
    chars = {t["status_char"] for t in result}
    assert chars == {"d", "!"}


def test_filter_status_chars_space_only_pending():
    result = apply_filters(SAMPLE_TASKS, status="incomplete", path_excludes="", status_chars=[" "])
    # Only plain pending tasks (no custom char)
    assert all(t["status_char"] == " " for t in result)
    assert not any(t["status_char"] == "d" for t in result)
    assert not any(t["status_char"] == "!" for t in result)


def test_filter_status_chars_empty_no_filter():
    result = apply_filters(SAMPLE_TASKS, status="all", path_excludes="", status_chars=[])
    assert len(result) == len(SAMPLE_TASKS)


def test_filter_status_chars_none_no_filter():
    result = apply_filters(SAMPLE_TASKS, status="all", path_excludes="", status_chars=None)
    assert len(result) == len(SAMPLE_TASKS)


def test_filter_status_chars_combined_with_status():
    # status="incomplete" + status_chars=["d"] → only [d] tasks that are incomplete
    result = apply_filters(SAMPLE_TASKS, status="incomplete", path_excludes="", status_chars=["d"])
    assert len(result) == 1
    assert result[0]["status"] == "incomplete"
    assert result[0]["status_char"] == "d"


def test_filter_status_chars_no_match_returns_empty():
    result = apply_filters(SAMPLE_TASKS, status="all", path_excludes="", status_chars=["?"])
    assert result == []
