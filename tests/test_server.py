"""Tests for server-level helper functions and new tools."""

import shutil
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from obsidian_tasks_mcp.server import _group_tasks, _matches_query, _score_match


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "sample_vault"


@pytest.fixture()
def sample_tasks() -> list[dict]:
    """A small list of task dicts exercising all group_by dimensions."""
    overdue_date = (date.today() - timedelta(days=365)).isoformat()
    future_date = (date.today() + timedelta(days=365)).isoformat()
    return [
        {
            "id": "Projects/work.md:1",
            "description": "Deploy service",
            "status": "incomplete",
            "tags": ["backend", "deploy"],
            "wikilinks": [],
            "due_date": overdue_date,
            "done_date": "",
            "reminder_time": "",
            "priority": "highest",
            "file_path": "Projects/work.md",
            "line_number": 1,
        },
        {
            "id": "Projects/work.md:2",
            "description": "Write tests",
            "status": "incomplete",
            "tags": ["backend"],
            "wikilinks": [],
            "due_date": future_date,
            "done_date": "",
            "reminder_time": "",
            "priority": "high",
            "file_path": "Projects/work.md",
            "line_number": 2,
        },
        {
            "id": "Journal/2026-03-14.md:5",
            "description": "Daily standup",
            "status": "incomplete",
            "tags": [],
            "wikilinks": [],
            "due_date": "",             # no_date
            "done_date": "",
            "reminder_time": "2026-03-14 09:00",
            "priority": "none",
            "file_path": "Journal/2026-03-14.md",
            "line_number": 5,
        },
    ]


# ---------------------------------------------------------------------------
# _score_match
# ---------------------------------------------------------------------------


def test_score_exact_phrase():
    assert _score_match("vercel ai sdk integration", "vercel ai sdk") == 100


def test_score_all_tokens():
    assert _score_match("check vercel and sdk usage", "vercel sdk") == 70


def test_score_partial_tokens():
    score = _score_match("check vercel usage", "vercel sdk")
    assert 0 < score < 70


def test_score_no_match():
    assert _score_match("completely unrelated text", "vercel sdk") == 0


def test_score_case_insensitive():
    assert _score_match("Vercel AI SDK", "vercel ai sdk") == 100


# ---------------------------------------------------------------------------
# _matches_query
# ---------------------------------------------------------------------------


def test_matches_query_description():
    task = {"description": "check out vercel ai sdk", "tags": [], "wikilinks": []}
    matched, score = _matches_query(task, "vercel")
    assert matched is True
    assert score > 0


def test_matches_query_tag():
    task = {"description": "some task", "tags": ["micro-mng-todo"], "wikilinks": []}
    matched, score = _matches_query(task, "micro")
    assert matched is True
    assert score >= 50


def test_matches_query_wikilink():
    task = {"description": "[[cal.com]] check", "tags": [], "wikilinks": ["cal.com"]}
    matched, score = _matches_query(task, "cal.com")
    assert matched is True


def test_matches_query_no_match():
    task = {"description": "unrelated task", "tags": [], "wikilinks": []}
    matched, score = _matches_query(task, "vercel")
    assert matched is False
    assert score == 0


# ---------------------------------------------------------------------------
# _group_tasks — group_by="file"
# ---------------------------------------------------------------------------


def test_group_by_file(sample_tasks):
    groups = _group_tasks(sample_tasks, "file")
    assert "Projects/work.md" in groups
    assert "Journal/2026-03-14.md" in groups
    assert len(groups["Projects/work.md"]) == 2
    assert len(groups["Journal/2026-03-14.md"]) == 1


# ---------------------------------------------------------------------------
# _group_tasks — group_by="tag"
# ---------------------------------------------------------------------------


def test_group_by_tag(sample_tasks):
    groups = _group_tasks(sample_tasks, "tag")
    assert "backend" in groups
    assert "deploy" in groups
    assert "untagged" in groups
    # "backend" tag appears on two tasks
    assert len(groups["backend"]) == 2
    # Task with no tags goes to "untagged"
    assert len(groups["untagged"]) == 1


# ---------------------------------------------------------------------------
# _group_tasks — group_by="priority"
# ---------------------------------------------------------------------------


def test_group_by_priority(sample_tasks):
    groups = _group_tasks(sample_tasks, "priority")
    assert "highest" in groups
    assert "high" in groups
    assert "none" in groups
    assert len(groups["highest"]) == 1
    assert len(groups["high"]) == 1
    assert len(groups["none"]) == 1


# ---------------------------------------------------------------------------
# _group_tasks — group_by="date"
# ---------------------------------------------------------------------------


def test_group_by_date_overdue(sample_tasks):
    groups = _group_tasks(sample_tasks, "date")
    assert "overdue" in groups
    overdue_descriptions = [t["description"] for t in groups["overdue"]]
    assert "Deploy service" in overdue_descriptions


def test_group_by_date_future(sample_tasks):
    groups = _group_tasks(sample_tasks, "date")
    assert "future" in groups
    future_descriptions = [t["description"] for t in groups["future"]]
    assert "Write tests" in future_descriptions


def test_group_by_date_no_date(sample_tasks):
    groups = _group_tasks(sample_tasks, "date")
    assert "no_date" in groups
    no_date_descriptions = [t["description"] for t in groups["no_date"]]
    assert "Daily standup" in no_date_descriptions


def test_group_by_invalid_raises(sample_tasks):
    with pytest.raises(ValueError, match="Unknown group_by"):
        _group_tasks(sample_tasks, "invalid")


# ---------------------------------------------------------------------------
# _group_tasks — empty task list
# ---------------------------------------------------------------------------


def test_group_empty_tasks():
    assert _group_tasks([], "file") == {}
    assert _group_tasks([], "tag") == {}
    assert _group_tasks([], "priority") == {}
    assert _group_tasks([], "date") == {}


# ---------------------------------------------------------------------------
# ISO week number fields in server tool responses
# ---------------------------------------------------------------------------


def _make_task(due_date: str = "", status: str = "incomplete") -> dict:
    """Minimal task dict for use in server function tests."""
    return {
        "id": "Projects/work.md:1",
        "description": "Test task",
        "status": status,
        "tags": [],
        "wikilinks": [],
        "due_date": due_date,
        "done_date": "",
        "reminder_time": "",
        "priority": "none",
        "file_path": "Projects/work.md",
        "line_number": 1,
    }


def test_list_tasks_returns_week_fields():
    """list_tasks response must include week_number, iso_year, weekday."""
    import obsidian_tasks_mcp.server as srv

    today = date.today()
    cal = today.isocalendar()

    with patch.object(srv.vault, "get_all_tasks", return_value=[_make_task()]):
        from obsidian_tasks_mcp.server import list_tasks

        result = list_tasks(status="all", path_excludes="")
    assert result["week_number"] == cal.week
    assert result["iso_year"] == cal.year
    assert result["weekday"] == cal.weekday
    assert result["date"] == today.isoformat()


def test_list_tasks_grouped_returns_week_fields():
    """list_tasks with group_by must also include week_number."""
    import obsidian_tasks_mcp.server as srv

    today = date.today()
    cal = today.isocalendar()

    with patch.object(srv.vault, "get_all_tasks", return_value=[_make_task()]):
        from obsidian_tasks_mcp.server import list_tasks

        result = list_tasks(status="all", path_excludes="", group_by="file")
    assert result["week_number"] == cal.week
    assert result["iso_year"] == cal.year
    assert result["weekday"] == cal.weekday


def test_get_daily_briefing_returns_week_fields():
    """get_daily_briefing response must include week_number, iso_year, weekday."""
    import obsidian_tasks_mcp.server as srv

    today = date.today()
    cal = today.isocalendar()

    with patch.object(srv.vault, "get_all_tasks", return_value=[]):
        from obsidian_tasks_mcp.server import get_daily_briefing

        result = get_daily_briefing()
    assert result["week_number"] == cal.week
    assert result["iso_year"] == cal.year
    assert result["weekday"] == cal.weekday
    assert result["date"] == today.isoformat()


def test_get_task_summary_returns_week_fields():
    """get_task_summary response must include week_number, iso_year, weekday."""
    import obsidian_tasks_mcp.server as srv

    today = date.today()
    cal = today.isocalendar()

    with patch.object(srv.vault, "get_all_tasks", return_value=[_make_task()]):
        from obsidian_tasks_mcp.server import get_task_summary

        result = get_task_summary(status="all", group_by="file", path_excludes="")
    assert result["week_number"] == cal.week
    assert result["iso_year"] == cal.year
    assert result["weekday"] == cal.weekday
    assert result["date"] == today.isoformat()


def test_list_tasks_due_from_filter():
    """list_tasks must forward due_from to apply_filters."""
    import obsidian_tasks_mcp.server as srv

    today = date.today()
    tomorrow = (today + timedelta(days=1)).isoformat()
    future = (today + timedelta(days=5)).isoformat()

    tasks = [_make_task(today.isoformat()), _make_task(future)]
    with patch.object(srv.vault, "get_all_tasks", return_value=tasks):
        from obsidian_tasks_mcp.server import list_tasks

        result = list_tasks(status="all", path_excludes="", due_from=tomorrow)
    assert all(t["due_date"] >= tomorrow for t in result["tasks"])
    assert result["total_count"] == 1


def test_list_tasks_due_to_filter():
    """list_tasks must forward due_to to apply_filters."""
    import obsidian_tasks_mcp.server as srv

    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    future = (today + timedelta(days=5)).isoformat()

    tasks = [_make_task(yesterday), _make_task(future)]
    with patch.object(srv.vault, "get_all_tasks", return_value=tasks):
        from obsidian_tasks_mcp.server import list_tasks

        result = list_tasks(status="all", path_excludes="", due_to=today.isoformat())
    assert all(t["due_date"] <= today.isoformat() for t in result["tasks"])
    assert result["total_count"] == 1


def test_get_task_summary_due_range_filter():
    """get_task_summary must forward due_from/due_to to apply_filters."""
    import obsidian_tasks_mcp.server as srv

    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    future = (today + timedelta(days=5)).isoformat()

    tasks = [_make_task(yesterday), _make_task(future)]
    with patch.object(srv.vault, "get_all_tasks", return_value=tasks):
        from obsidian_tasks_mcp.server import get_task_summary

        result = get_task_summary(
            status="all",
            group_by="file",
            path_excludes="",
            due_from=today.isoformat(),
        )
    assert result["total_count"] == 1

