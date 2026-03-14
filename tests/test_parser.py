"""Unit tests for obsidian_tasks_mcp.parser."""

import pytest

from obsidian_tasks_mcp.parser import (
    format_task_line,
    is_task_line,
    parse_task_line,
)


# ---------------------------------------------------------------------------
# is_task_line
# ---------------------------------------------------------------------------


def test_is_task_line_incomplete():
    assert is_task_line("- [ ] Some task") is True


def test_is_task_line_complete():
    assert is_task_line("- [x] Done task") is True


def test_is_task_line_uppercase_x():
    assert is_task_line("- [X] Done task") is True


def test_is_task_line_heading():
    assert is_task_line("# Heading") is False


def test_is_task_line_plain_text():
    assert is_task_line("Some plain text") is False


def test_is_task_line_bullet_no_checkbox():
    assert is_task_line("- Just a list item") is False


# ---------------------------------------------------------------------------
# parse_task_line — basic fields
# ---------------------------------------------------------------------------


def test_parse_returns_none_for_non_task():
    assert parse_task_line("# Heading") is None
    assert parse_task_line("- Just a bullet") is None
    assert parse_task_line("Some text") is None


def test_parse_incomplete_task():
    task = parse_task_line("- [ ] Review end-to-end flow", "Projects/work.md", 5)
    assert task is not None
    assert task["status"] == "incomplete"
    assert task["description"] == "Review end-to-end flow"
    assert task["file_path"] == "Projects/work.md"
    assert task["line_number"] == 5
    assert task["id"] == "Projects/work.md:5"


def test_parse_complete_task():
    task = parse_task_line("- [x] Set up CI/CD pipeline ✅ 2026-03-10", "Projects/work.md", 7)
    assert task is not None
    assert task["status"] == "complete"
    assert task["description"] == "Set up CI/CD pipeline"
    assert task["done_date"] == "2026-03-10"


def test_parse_complete_task_uppercase_x():
    task = parse_task_line("- [X] Done with uppercase", "file.md", 1)
    assert task is not None
    assert task["status"] == "complete"


def test_parse_task_default_file_and_line():
    task = parse_task_line("- [ ] A task")
    assert task is not None
    assert task["file_path"] == ""
    assert task["line_number"] == 0


# ---------------------------------------------------------------------------
# parse_task_line — due date
# ---------------------------------------------------------------------------


def test_parse_due_date():
    task = parse_task_line("- [ ] Review end-to-end flow 📅 2026-03-14", "f.md", 1)
    assert task["due_date"] == "2026-03-14"


def test_parse_due_date_not_in_description():
    task = parse_task_line("- [ ] Review end-to-end flow 📅 2026-03-14", "f.md", 1)
    assert "2026-03-14" not in task["description"]
    assert "📅" not in task["description"]


def test_parse_no_due_date():
    task = parse_task_line("- [ ] Just a task", "f.md", 1)
    assert task["due_date"] == ""


# ---------------------------------------------------------------------------
# parse_task_line — priority
# ---------------------------------------------------------------------------


def test_parse_priority_highest():
    task = parse_task_line("- [ ] Task 🔺", "f.md", 1)
    assert task["priority"] == "highest"


def test_parse_priority_high():
    task = parse_task_line("- [ ] Task ⬆️", "f.md", 1)
    assert task["priority"] == "high"


def test_parse_priority_medium():
    task = parse_task_line("- [ ] Task 🔼", "f.md", 1)
    assert task["priority"] == "medium"


def test_parse_priority_low():
    task = parse_task_line("- [ ] Task 🔽", "f.md", 1)
    assert task["priority"] == "low"


def test_parse_priority_lowest():
    task = parse_task_line("- [ ] Task ⬇️", "f.md", 1)
    assert task["priority"] == "lowest"


def test_parse_priority_none():
    task = parse_task_line("- [ ] Task without priority", "f.md", 1)
    assert task["priority"] == "none"


def test_priority_emoji_not_in_description():
    task = parse_task_line("- [ ] Task 🔺 📅 2026-03-14", "f.md", 1)
    assert "🔺" not in task["description"]


# ---------------------------------------------------------------------------
# parse_task_line — tags
# ---------------------------------------------------------------------------


def test_parse_single_tag():
    task = parse_task_line("- [ ] Task #micro-mng-todo", "f.md", 1)
    assert "micro-mng-todo" in task["tags"]


def test_parse_multiple_tags():
    task = parse_task_line("- [ ] Task #micro-mng-todo #work", "f.md", 1)
    assert "micro-mng-todo" in task["tags"]
    assert "work" in task["tags"]


def test_tags_not_in_description():
    task = parse_task_line("- [ ] Task #micro-mng-todo", "f.md", 1)
    assert "#micro-mng-todo" not in task["description"]
    assert "micro-mng-todo" not in task["description"]


def test_parse_no_tags():
    task = parse_task_line("- [ ] Task without tags", "f.md", 1)
    assert task["tags"] == []


# ---------------------------------------------------------------------------
# format_task_line
# ---------------------------------------------------------------------------


def test_format_incomplete_no_extras():
    task = {
        "status": "incomplete",
        "description": "Review PR",
        "priority": "none",
        "due_date": "",
        "done_date": "",
        "tags": [],
    }
    assert format_task_line(task) == "- [ ] Review PR"


def test_format_complete_with_done_date():
    task = {
        "status": "complete",
        "description": "Deploy service",
        "priority": "none",
        "due_date": "",
        "done_date": "2026-03-14",
        "tags": [],
    }
    line = format_task_line(task)
    assert line.startswith("- [x]")
    assert "✅ 2026-03-14" in line


def test_format_with_priority_and_due():
    task = {
        "status": "incomplete",
        "description": "Review PR for auth module",
        "priority": "highest",
        "due_date": "2026-03-15",
        "done_date": "",
        "tags": ["micro-mng-todo"],
    }
    line = format_task_line(task)
    assert "🔺" in line
    assert "📅 2026-03-15" in line
    assert "#micro-mng-todo" in line
    assert "Review PR for auth module" in line


def test_format_with_multiple_tags():
    task = {
        "status": "incomplete",
        "description": "Task",
        "priority": "none",
        "due_date": "",
        "done_date": "",
        "tags": ["tagA", "tagB"],
    }
    line = format_task_line(task)
    assert "#tagA" in line
    assert "#tagB" in line


# ---------------------------------------------------------------------------
# Round-trip: parse → format → parse
# ---------------------------------------------------------------------------


def test_roundtrip_full():
    original = "- [ ] Review PR for auth module 🔺 📅 2026-03-15 #micro-mng-todo"
    task = parse_task_line(original, "test.md", 1)
    assert task is not None
    reformatted = format_task_line(task)
    assert "🔺" in reformatted
    assert "📅 2026-03-15" in reformatted
    assert "#micro-mng-todo" in reformatted
    assert "Review PR for auth module" in reformatted
    # Re-parsing should yield the same structured data
    task2 = parse_task_line(reformatted, "test.md", 1)
    assert task2 is not None
    assert task2["description"] == task["description"]
    assert task2["due_date"] == task["due_date"]
    assert task2["priority"] == task["priority"]
    assert task2["tags"] == task["tags"]


def test_roundtrip_complete_task():
    original = "- [x] Set up CI/CD pipeline ✅ 2026-03-10"
    task = parse_task_line(original, "f.md", 1)
    assert task is not None
    reformatted = format_task_line(task)
    task2 = parse_task_line(reformatted, "f.md", 1)
    assert task2 is not None
    assert task2["status"] == "complete"
    assert task2["done_date"] == "2026-03-10"
