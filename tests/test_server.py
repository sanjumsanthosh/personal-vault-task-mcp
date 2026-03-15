"""Tests for server-level helper functions and new tools."""

import shutil
from datetime import date, timedelta
from pathlib import Path

import pytest

from obsidian_tasks_mcp.server import _group_tasks, _matches_query, _score_match, get_daily_briefing


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
# get_daily_briefing — day_of_week and week_number fields
# ---------------------------------------------------------------------------


def test_daily_briefing_includes_day_of_week(tmp_path, monkeypatch):
    """get_daily_briefing() should include a human-readable day name."""
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    result = get_daily_briefing()
    today = date.today()
    assert result["day_of_week"] == today.strftime("%A")


def test_daily_briefing_includes_week_number(tmp_path, monkeypatch):
    """get_daily_briefing() should include the ISO week number."""
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    result = get_daily_briefing()
    today = date.today()
    assert result["week_number"] == today.isocalendar()[1]


def test_daily_briefing_date_field(tmp_path, monkeypatch):
    """get_daily_briefing() date field should match today's ISO date."""
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    result = get_daily_briefing()
    assert result["date"] == date.today().isoformat()

