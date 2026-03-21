"""Unit tests for obsidian_tasks_mcp.parser."""

import pytest

from obsidian_tasks_mcp.parser import (
    format_task_line,
    is_task_line,
    parse_inline_metadata,
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
# parse_task_line — custom / Obsidian-style checkbox statuses
# ---------------------------------------------------------------------------


def test_is_task_line_custom_status_doing():
    assert is_task_line("- [d] Working on this") is True


def test_is_task_line_custom_status_blocked():
    assert is_task_line("- [!] Blocked task") is True


def test_is_task_line_custom_status_dash():
    assert is_task_line("- [-] Cancelled task") is True


def test_is_task_line_custom_status_question():
    assert is_task_line("- [?] Needs clarification") is True


def test_parse_custom_status_doing_is_incomplete():
    task = parse_task_line("- [d] Working on this", "Projects/work.md", 3)
    assert task is not None
    assert task["status"] == "incomplete"
    assert task["description"] == "Working on this"


def test_parse_custom_status_blocked_is_incomplete():
    task = parse_task_line("- [!] Blocked task", "Projects/work.md", 4)
    assert task is not None
    assert task["status"] == "incomplete"
    assert task["description"] == "Blocked task"


def test_parse_custom_status_dash_is_incomplete():
    task = parse_task_line("- [-] Cancelled task", "Projects/work.md", 5)
    assert task is not None
    assert task["status"] == "incomplete"


def test_parse_custom_status_uppercase_not_x_is_incomplete():
    task = parse_task_line("- [D] In progress uppercase", "file.md", 1)
    assert task is not None
    assert task["status"] == "incomplete"


def test_parse_custom_status_preserves_description_and_metadata():
    task = parse_task_line("- [d] Working on auth 📅 2026-03-20 #backend", "Projects/work.md", 8)
    assert task is not None
    assert task["status"] == "incomplete"
    assert task["description"] == "Working on auth"
    assert task["due_date"] == "2026-03-20"
    assert "backend" in task["tags"]


def test_parse_stores_status_char_space():
    task = parse_task_line("- [ ] Normal pending", "f.md", 1)
    assert task is not None
    assert task["status_char"] == " "


def test_parse_stores_status_char_x():
    task = parse_task_line("- [x] Done task", "f.md", 1)
    assert task is not None
    assert task["status_char"] == "x"


def test_parse_stores_status_char_custom():
    task = parse_task_line("- [d] Doing task", "f.md", 1)
    assert task is not None
    assert task["status_char"] == "d"


def test_parse_stores_status_char_blocked():
    task = parse_task_line("- [!] Blocked", "f.md", 1)
    assert task is not None
    assert task["status_char"] == "!"


def test_format_preserves_custom_status_char():
    """format_task_line must write the original checkbox char for custom statuses."""
    task = parse_task_line("- [d] Working on this", "f.md", 1)
    assert task is not None
    line = format_task_line(task)
    assert line.startswith("- [d]")


def test_format_preserves_blocked_char():
    task = parse_task_line("- [!] Blocked", "f.md", 1)
    assert task is not None
    line = format_task_line(task)
    assert line.startswith("- [!]")


def test_format_custom_char_not_x_cannot_produce_complete():
    """A task with a custom status_char but status=incomplete must NOT get [x]."""
    task = {
        "status": "incomplete",
        "status_char": "d",
        "description": "Doing task",
        "priority": "none",
        "due_date": "",
        "done_date": "",
        "tags": [],
    }
    line = format_task_line(task)
    assert line.startswith("- [d]")
    assert not line.startswith("- [x]")


def test_format_status_char_x_on_incomplete_falls_back_to_space():
    """If somehow status_char='x' but status='incomplete', output must be '[ ]'."""
    task = {
        "status": "incomplete",
        "status_char": "x",
        "description": "Should not be [x]",
        "priority": "none",
        "due_date": "",
        "done_date": "",
        "tags": [],
    }
    line = format_task_line(task)
    assert line.startswith("- [ ]")


def test_format_status_char_uppercase_x_on_incomplete_falls_back_to_space():
    """If somehow status_char='X' but status='incomplete', output must be '[ ]'."""
    task = {
        "status": "incomplete",
        "status_char": "X",
        "description": "Should not be [X]",
        "priority": "none",
        "due_date": "",
        "done_date": "",
        "tags": [],
    }
    line = format_task_line(task)
    assert line.startswith("- [ ]")


def test_roundtrip_custom_status_char():
    """parse → format → parse must preserve the custom checkbox character."""
    original = "- [d] Working on auth 📅 2026-03-20 #backend"
    task = parse_task_line(original, "f.md", 1)
    assert task is not None
    reformatted = format_task_line(task)
    assert reformatted.startswith("- [d]")
    task2 = parse_task_line(reformatted, "f.md", 1)
    assert task2 is not None
    assert task2["status"] == "incomplete"
    assert task2["status_char"] == "d"
    assert task2["description"] == task["description"]
    assert task2["due_date"] == task["due_date"]
    assert task2["tags"] == task["tags"]


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


# ---------------------------------------------------------------------------
# parse_task_line — reminder_time (⏰)
# ---------------------------------------------------------------------------


def test_parse_reminder_date_only():
    task = parse_task_line("- [ ] Task ⏰ 2026-03-15", "f.md", 1)
    assert task is not None
    assert task["reminder_time"] == "2026-03-15"


def test_parse_reminder_with_time():
    task = parse_task_line("- [ ] Task ⏰ 2026-03-15 10:00", "f.md", 1)
    assert task is not None
    assert task["reminder_time"] == "2026-03-15 10:00"


def test_parse_reminder_with_due_date():
    task = parse_task_line("- [ ] Task ⏰ 2026-03-15 10:00 📅 2026-03-16", "f.md", 1)
    assert task is not None
    assert task["reminder_time"] == "2026-03-15 10:00"
    assert task["due_date"] == "2026-03-16"


def test_parse_reminder_with_priority():
    task = parse_task_line("- [ ] Task 🔺 ⏰ 2026-03-15 09:00 📅 2026-03-15 #tag", "f.md", 1)
    assert task is not None
    assert task["priority"] == "highest"
    assert task["reminder_time"] == "2026-03-15 09:00"
    assert task["due_date"] == "2026-03-15"
    assert "tag" in task["tags"]


def test_parse_no_reminder():
    task = parse_task_line("- [ ] Task without reminder", "f.md", 1)
    assert task is not None
    assert task["reminder_time"] == ""


def test_parse_reminder_not_in_description():
    task = parse_task_line("- [ ] Task ⏰ 2026-03-15 10:00", "f.md", 1)
    assert task is not None
    assert "⏰" not in task["description"]
    assert "2026-03-15" not in task["description"]
    assert "10:00" not in task["description"]


# ---------------------------------------------------------------------------
# format_task_line — reminder_time
# ---------------------------------------------------------------------------


def test_format_with_reminder_date_only():
    task = {
        "status": "incomplete",
        "description": "Task",
        "priority": "none",
        "reminder_time": "2026-03-15",
        "due_date": "",
        "done_date": "",
        "tags": [],
    }
    line = format_task_line(task)
    assert "⏰ 2026-03-15" in line


def test_format_with_reminder_and_due():
    task = {
        "status": "incomplete",
        "description": "Task",
        "priority": "none",
        "reminder_time": "2026-03-15 09:00",
        "due_date": "2026-03-15",
        "done_date": "",
        "tags": [],
    }
    line = format_task_line(task)
    assert "⏰ 2026-03-15 09:00" in line
    assert "📅 2026-03-15" in line
    # ⏰ must appear before 📅
    assert line.index("⏰") < line.index("📅")


def test_format_reminder_ordering():
    """priority → ⏰ reminder → 📅 due → ✅ done → #tags"""
    task = {
        "status": "incomplete",
        "description": "Review PR",
        "priority": "highest",
        "reminder_time": "2026-03-15 09:00",
        "due_date": "2026-03-15",
        "done_date": "",
        "tags": ["work"],
    }
    line = format_task_line(task)
    assert line.index("🔺") < line.index("⏰") < line.index("📅") < line.index("#work")


def test_format_no_reminder():
    task = {
        "status": "incomplete",
        "description": "Task",
        "priority": "none",
        "reminder_time": "",
        "due_date": "2026-03-15",
        "done_date": "",
        "tags": [],
    }
    line = format_task_line(task)
    assert "⏰" not in line
    assert "📅 2026-03-15" in line


# ---------------------------------------------------------------------------
# Round-trip: parse → format → parse (with reminder)
# ---------------------------------------------------------------------------


def test_roundtrip_with_reminder():
    original = "- [ ] Review PR for auth module 🔺 ⏰ 2026-03-15 09:00 📅 2026-03-15 #micro-mng-todo"
    task = parse_task_line(original, "test.md", 1)
    assert task is not None
    assert task["reminder_time"] == "2026-03-15 09:00"
    reformatted = format_task_line(task)
    assert "⏰ 2026-03-15 09:00" in reformatted
    assert "📅 2026-03-15" in reformatted
    task2 = parse_task_line(reformatted, "test.md", 1)
    assert task2 is not None
    assert task2["reminder_time"] == "2026-03-15 09:00"
    assert task2["due_date"] == "2026-03-15"
    assert task2["description"] == task["description"]
    assert task2["priority"] == task["priority"]
    assert task2["tags"] == task["tags"]


def test_roundtrip_reminder_date_only():
    original = "- [ ] Daily standup ⏰ 2026-03-15"
    task = parse_task_line(original, "test.md", 1)
    assert task is not None
    reformatted = format_task_line(task)
    task2 = parse_task_line(reformatted, "test.md", 1)
    assert task2 is not None
    assert task2["reminder_time"] == "2026-03-15"
    assert task2["description"] == "Daily standup"


# ---------------------------------------------------------------------------
# Tag immediately before due date — regression tests
# ---------------------------------------------------------------------------


def test_parse_tag_immediately_before_due_date():
    """Tag directly before 📅 (with a separating space) must be detected."""
    task = parse_task_line(
        "- [ ] compare llms to see which one is good? #micro-mng-todo 📅 2026-03-21",
        "f.md", 1,
    )
    assert task is not None
    assert task["due_date"] == "2026-03-21"
    assert "micro-mng-todo" in task["tags"]
    assert task["description"] == "compare llms to see which one is good?"


def test_parse_tag_immediately_before_due_date_no_space():
    """Tag followed by 📅 with *no* space between them must still be detected."""
    task = parse_task_line(
        "- [ ] Task #micro-mng-todo📅 2026-03-21",
        "f.md", 1,
    )
    assert task is not None
    assert task["due_date"] == "2026-03-21"
    assert "micro-mng-todo" in task["tags"]
    assert task["description"] == "Task"


def test_parse_multiple_tags_one_before_due_date():
    """One tag before and one tag after the due date are both detected."""
    task = parse_task_line(
        "- [ ] compare llms? #micro-mng-todo 📅 2026-03-21 #work",
        "f.md", 1,
    )
    assert task is not None
    assert task["due_date"] == "2026-03-21"
    assert "micro-mng-todo" in task["tags"]
    assert "work" in task["tags"]
    assert task["description"] == "compare llms?"


def test_tag_before_due_date_not_in_description():
    """Tags and the due-date marker must not appear in the cleaned description."""
    task = parse_task_line(
        "- [ ] compare llms? #micro-mng-todo 📅 2026-03-21",
        "f.md", 1,
    )
    assert task is not None
    assert "#micro-mng-todo" not in task["description"]
    assert "📅" not in task["description"]
    assert "2026-03-21" not in task["description"]


def test_roundtrip_tag_before_due_date():
    """parse → format → parse must preserve all fields when tag precedes due date."""
    original = "- [ ] compare llms to see which one is good? #micro-mng-todo 📅 2026-03-21"
    task = parse_task_line(original, "f.md", 1)
    assert task is not None
    reformatted = format_task_line(task)
    task2 = parse_task_line(reformatted, "f.md", 1)
    assert task2 is not None
    assert task2["description"] == task["description"]
    assert task2["due_date"] == task["due_date"]
    assert task2["tags"] == task["tags"]


def test_roundtrip_tag_before_due_date_with_priority():
    """Round-trip with priority + tag-before-due-date combination."""
    original = "- [ ] Review PR 🔺 #micro-mng-todo 📅 2026-03-21"
    task = parse_task_line(original, "f.md", 1)
    assert task is not None
    assert task["priority"] == "highest"
    assert "micro-mng-todo" in task["tags"]
    assert task["due_date"] == "2026-03-21"
    reformatted = format_task_line(task)
    task2 = parse_task_line(reformatted, "f.md", 1)
    assert task2 is not None
    assert task2["priority"] == task["priority"]
    assert task2["tags"] == task["tags"]
    assert task2["due_date"] == task["due_date"]


# ---------------------------------------------------------------------------
# parse_inline_metadata
# ---------------------------------------------------------------------------


def test_parse_inline_metadata_tag_before_due():
    clean, tags, due = parse_inline_metadata(
        "compare llms? #micro-mng-todo 📅 2026-03-21"
    )
    assert clean == "compare llms?"
    assert tags == ["micro-mng-todo"]
    assert due == "2026-03-21"


def test_parse_inline_metadata_tag_after_due():
    clean, tags, due = parse_inline_metadata(
        "compare llms? 📅 2026-03-21 #micro-mng-todo"
    )
    assert clean == "compare llms?"
    assert tags == ["micro-mng-todo"]
    assert due == "2026-03-21"


def test_parse_inline_metadata_no_metadata():
    clean, tags, due = parse_inline_metadata("plain description text")
    assert clean == "plain description text"
    assert tags == []
    assert due == ""


def test_parse_inline_metadata_only_tag():
    clean, tags, due = parse_inline_metadata("do something #work")
    assert clean == "do something"
    assert tags == ["work"]
    assert due == ""


def test_parse_inline_metadata_only_due():
    clean, tags, due = parse_inline_metadata("do something 📅 2026-03-21")
    assert clean == "do something"
    assert tags == []
    assert due == "2026-03-21"


def test_parse_inline_metadata_multiple_tags():
    clean, tags, due = parse_inline_metadata(
        "task #alpha #beta 📅 2026-03-21"
    )
    assert clean == "task"
    assert "alpha" in tags
    assert "beta" in tags
    assert due == "2026-03-21"

