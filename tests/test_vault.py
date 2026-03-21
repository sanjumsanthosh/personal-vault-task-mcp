"""Integration tests for obsidian_tasks_mcp.vault using the sample vault fixtures."""

import shutil
from pathlib import Path

import pytest

from obsidian_tasks_mcp.vault import VaultManager

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "sample_vault"


@pytest.fixture()
def vault_copy(tmp_path: Path) -> Path:
    """Copy the sample vault to a temp dir so tests can modify it safely."""
    dest = tmp_path / "vault"
    shutil.copytree(FIXTURES_DIR, dest)
    return dest


@pytest.fixture()
def vault(vault_copy: Path) -> VaultManager:
    return VaultManager(vault_copy)


# ---------------------------------------------------------------------------
# get_all_tasks
# ---------------------------------------------------------------------------


def test_get_all_tasks_returns_list(vault: VaultManager):
    tasks = vault.get_all_tasks()
    assert isinstance(tasks, list)
    assert len(tasks) > 0


def test_get_all_tasks_have_required_keys(vault: VaultManager):
    tasks = vault.get_all_tasks()
    required = {"id", "description", "status", "status_char", "tags", "due_date", "priority", "file_path", "line_number"}
    for task in tasks:
        assert required.issubset(task.keys()), f"Missing keys in {task}"


def test_get_all_tasks_from_projects(vault: VaultManager):
    tasks = vault.get_all_tasks()
    project_tasks = [t for t in tasks if "Projects" in t["file_path"]]
    assert len(project_tasks) > 0


def test_get_all_tasks_from_journal(vault: VaultManager):
    tasks = vault.get_all_tasks()
    journal_tasks = [t for t in tasks if "Journal" in t["file_path"]]
    assert len(journal_tasks) > 0


def test_get_all_tasks_empty_vault(tmp_path: Path):
    vm = VaultManager(tmp_path / "nonexistent")
    assert vm.get_all_tasks() == []


def test_task_ids_use_posix_paths(vault: VaultManager):
    tasks = vault.get_all_tasks()
    for task in tasks:
        assert "\\" not in task["id"], "IDs must use forward slashes"
        assert "\\" not in task["file_path"]


# ---------------------------------------------------------------------------
# update_task — mark_done
# ---------------------------------------------------------------------------


def test_update_mark_done(vault: VaultManager):
    tasks = vault.get_all_tasks()
    incomplete = next(t for t in tasks if t["status"] == "incomplete")
    updated = vault.update_task(incomplete["file_path"], incomplete["line_number"], "mark_done")
    assert updated["status"] == "complete"
    assert updated["done_date"] != ""


def test_update_mark_done_persisted(vault: VaultManager):
    tasks = vault.get_all_tasks()
    incomplete = next(t for t in tasks if t["status"] == "incomplete")
    vault.update_task(incomplete["file_path"], incomplete["line_number"], "mark_done")
    # Re-read
    refreshed = vault.get_all_tasks()
    found = next(
        (t for t in refreshed if t["file_path"] == incomplete["file_path"] and t["line_number"] == incomplete["line_number"]),
        None,
    )
    assert found is not None
    assert found["status"] == "complete"


# ---------------------------------------------------------------------------
# update_task — mark_undone
# ---------------------------------------------------------------------------


def test_update_mark_undone(vault: VaultManager):
    tasks = vault.get_all_tasks()
    complete = next(t for t in tasks if t["status"] == "complete")
    updated = vault.update_task(complete["file_path"], complete["line_number"], "mark_undone")
    assert updated["status"] == "incomplete"
    assert updated["done_date"] == ""


def test_update_mark_undone_resets_to_plain_pending(vault: VaultManager):
    """mark_undone must write '- [ ]', not '- [x]' or any custom char."""
    tasks = vault.get_all_tasks()
    complete = next(t for t in tasks if t["status"] == "complete")
    vault.update_task(complete["file_path"], complete["line_number"], "mark_undone")
    refreshed = vault.get_all_tasks()
    found = next(
        t for t in refreshed
        if t["file_path"] == complete["file_path"] and t["line_number"] == complete["line_number"]
    )
    assert found["status"] == "incomplete"
    assert found["status_char"] == " "


# ---------------------------------------------------------------------------
# update_task — mark_doing
# ---------------------------------------------------------------------------


def test_update_mark_doing_sets_d_status_char(vault: VaultManager):
    """mark_doing on a plain pending task must write [d]."""
    tasks = vault.get_all_tasks()
    pending = next(t for t in tasks if t["status"] == "incomplete" and t.get("status_char") == " ")
    updated = vault.update_task(pending["file_path"], pending["line_number"], "mark_doing")
    assert updated["status"] == "incomplete"
    assert updated["status_char"] == "d"


def test_update_mark_doing_persisted(vault: VaultManager):
    """mark_doing must persist [d] to disk."""
    tasks = vault.get_all_tasks()
    pending = next(t for t in tasks if t["status"] == "incomplete" and t.get("status_char") == " ")
    vault.update_task(pending["file_path"], pending["line_number"], "mark_doing")
    refreshed = vault.get_all_tasks()
    found = next(
        t for t in refreshed
        if t["file_path"] == pending["file_path"] and t["line_number"] == pending["line_number"]
    )
    assert found["status_char"] == "d"
    assert found["status"] == "incomplete"


def test_update_mark_doing_clears_done_date(vault: VaultManager):
    """mark_doing on a complete task must clear done_date and set [d]."""
    tasks = vault.get_all_tasks()
    complete = next(t for t in tasks if t["status"] == "complete")
    updated = vault.update_task(complete["file_path"], complete["line_number"], "mark_doing")
    assert updated["status"] == "incomplete"
    assert updated["status_char"] == "d"
    assert updated["done_date"] == ""


def test_bulk_update_mark_doing(vault: VaultManager):
    """bulk_update_tasks with mark_doing must set [d] on all matched tasks."""
    tasks = vault.get_all_tasks()
    pending = [t for t in tasks if t["status"] == "incomplete" and t.get("status_char") == " "]
    ids = [t["id"] for t in pending[:2]]
    result = vault.bulk_update_tasks(ids, "mark_doing")
    assert result["updated_count"] == len(ids)
    refreshed = vault.get_all_tasks()
    for tid in ids:
        fp, ln = tid.rsplit(":", 1)
        found = next(t for t in refreshed if t["file_path"] == fp and t["line_number"] == int(ln))
        assert found["status_char"] == "d"


# ---------------------------------------------------------------------------
# update_task — custom status_char preservation
# ---------------------------------------------------------------------------


def test_custom_status_char_preserved_on_add_tag(vault: VaultManager):
    """Adding a tag to a [d] task must keep the [d] bracket."""
    tasks = vault.get_all_tasks()
    doing = next(t for t in tasks if t.get("status_char") == "d")
    vault.update_task(doing["file_path"], doing["line_number"], "add_tag", "in-progress")
    refreshed = vault.get_all_tasks()
    found = next(
        t for t in refreshed
        if t["file_path"] == doing["file_path"] and t["line_number"] == doing["line_number"]
    )
    assert found["status_char"] == "d"
    assert "in-progress" in found["tags"]


def test_custom_status_char_preserved_on_add_due_date(vault: VaultManager):
    """Setting a due date on a [d] task must keep the [d] bracket."""
    tasks = vault.get_all_tasks()
    doing = next(t for t in tasks if t.get("status_char") == "d")
    vault.update_task(doing["file_path"], doing["line_number"], "add_due_date", "2026-06-01")
    refreshed = vault.get_all_tasks()
    found = next(
        t for t in refreshed
        if t["file_path"] == doing["file_path"] and t["line_number"] == doing["line_number"]
    )
    assert found["status_char"] == "d"
    assert found["due_date"] == "2026-06-01"


def test_custom_status_char_mark_done_writes_x(vault: VaultManager):
    """mark_done on a [d] task must write [x]."""
    tasks = vault.get_all_tasks()
    doing = next(t for t in tasks if t.get("status_char") == "d")
    updated = vault.update_task(doing["file_path"], doing["line_number"], "mark_done")
    assert updated["status"] == "complete"
    refreshed = vault.get_all_tasks()
    found = next(
        t for t in refreshed
        if t["file_path"] == doing["file_path"] and t["line_number"] == doing["line_number"]
    )
    assert found["status_char"] == "x"


# ---------------------------------------------------------------------------
# update_task — due date operations
# ---------------------------------------------------------------------------


def test_update_add_due_date(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = next(t for t in tasks if not t["due_date"])
    updated = vault.update_task(task["file_path"], task["line_number"], "add_due_date", "2026-04-01")
    assert updated["due_date"] == "2026-04-01"


def test_update_reschedule(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = next(t for t in tasks if t["due_date"])
    updated = vault.update_task(task["file_path"], task["line_number"], "reschedule", "2026-05-01")
    assert updated["due_date"] == "2026-05-01"


# ---------------------------------------------------------------------------
# update_task — tag operations
# ---------------------------------------------------------------------------


def test_update_add_tag(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = next(t for t in tasks if "new-tag" not in t["tags"])
    updated = vault.update_task(task["file_path"], task["line_number"], "add_tag", "new-tag")
    assert "new-tag" in updated["tags"]


def test_update_add_tag_with_hash_prefix(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = next(t for t in tasks if "new-tag" not in t["tags"])
    updated = vault.update_task(task["file_path"], task["line_number"], "add_tag", "#new-tag")
    assert "new-tag" in updated["tags"]


def test_update_remove_tag(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = next(t for t in tasks if t["tags"])
    tag_to_remove = task["tags"][0]
    updated = vault.update_task(task["file_path"], task["line_number"], "remove_tag", tag_to_remove)
    assert tag_to_remove not in updated["tags"]


# ---------------------------------------------------------------------------
# update_task — description
# ---------------------------------------------------------------------------


def test_update_description(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = tasks[0]
    updated = vault.update_task(task["file_path"], task["line_number"], "update_description", "New description text")
    assert updated["description"] == "New description text"


# ---------------------------------------------------------------------------
# update_task — error cases
# ---------------------------------------------------------------------------


def test_update_invalid_line_number(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = tasks[0]
    with pytest.raises(ValueError, match="out of range"):
        vault.update_task(task["file_path"], 99999, "mark_done")


def test_update_non_task_line(vault: VaultManager):
    with pytest.raises(ValueError, match="not a task line"):
        vault.update_task("Projects/work.md", 1, "mark_done")  # line 1 is a heading


def test_update_missing_file(vault: VaultManager):
    with pytest.raises(FileNotFoundError):
        vault.update_task("nonexistent/file.md", 1, "mark_done")


def test_update_unknown_operation(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = tasks[0]
    with pytest.raises(ValueError, match="Unknown operation"):
        vault.update_task(task["file_path"], task["line_number"], "teleport")


# ---------------------------------------------------------------------------
# create_task — inbox
# ---------------------------------------------------------------------------


def test_create_task_inbox(vault: VaultManager):
    result = vault.create_task("New inbox task", target="inbox")
    assert result["description"] == "New inbox task"
    assert result["file_path"] == "Inbox.md"
    assert (vault.vault_path / "Inbox.md").exists()


def test_create_task_inbox_appended(vault: VaultManager):
    vault.create_task("First task", target="inbox")
    vault.create_task("Second task", target="inbox")
    content = (vault.vault_path / "Inbox.md").read_text(encoding="utf-8")
    assert "First task" in content
    assert "Second task" in content


# ---------------------------------------------------------------------------
# create_task — file target
# ---------------------------------------------------------------------------


def test_create_task_file_target(vault: VaultManager):
    result = vault.create_task("File task", target="file", file_path="Projects/work.md")
    assert result["file_path"] == "Projects/work.md"
    content = (vault.vault_path / "Projects" / "work.md").read_text(encoding="utf-8")
    assert "File task" in content


def test_create_task_file_target_missing_path(vault: VaultManager):
    with pytest.raises(ValueError, match="file_path must be provided"):
        vault.create_task("Task", target="file")


# ---------------------------------------------------------------------------
# create_task — with optional fields
# ---------------------------------------------------------------------------


def test_create_task_with_tag(vault: VaultManager):
    result = vault.create_task("Tagged task", tag="my-tag", target="inbox")
    assert "my-tag" in result["tags"]


def test_create_task_with_due_date(vault: VaultManager):
    result = vault.create_task("Due task", due_date="2026-04-15", target="inbox")
    assert result["due_date"] == "2026-04-15"


def test_create_task_with_priority(vault: VaultManager):
    result = vault.create_task("Priority task", priority="high", target="inbox")
    assert result["priority"] == "high"
    content = (vault.vault_path / "Inbox.md").read_text(encoding="utf-8")
    assert "⬆️" in content


def test_create_task_unknown_target(vault: VaultManager):
    with pytest.raises(ValueError, match="Unknown target"):
        vault.create_task("Task", target="invalid_target")


# ---------------------------------------------------------------------------
# create_task — reminder_time
# ---------------------------------------------------------------------------


def test_create_task_with_reminder_date(vault: VaultManager):
    result = vault.create_task("Reminder task", reminder_time="2026-04-15", target="inbox")
    assert result["reminder_time"] == "2026-04-15"
    content = (vault.vault_path / "Inbox.md").read_text(encoding="utf-8")
    assert "⏰ 2026-04-15" in content


def test_create_task_with_reminder_datetime(vault: VaultManager):
    result = vault.create_task("Stand-up", reminder_time="2026-04-15 09:00", target="inbox")
    assert result["reminder_time"] == "2026-04-15 09:00"
    content = (vault.vault_path / "Inbox.md").read_text(encoding="utf-8")
    assert "⏰ 2026-04-15 09:00" in content


def test_create_task_reminder_before_due_date(vault: VaultManager):
    result = vault.create_task(
        "Task with reminder and due",
        reminder_time="2026-04-15 09:00",
        due_date="2026-04-16",
        target="inbox",
    )
    content = (vault.vault_path / "Inbox.md").read_text(encoding="utf-8")
    assert content.index("⏰") < content.index("📅")


# ---------------------------------------------------------------------------
# update_task — add_reminder / remove_reminder
# ---------------------------------------------------------------------------


def test_update_add_reminder(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = next(t for t in tasks if t["status"] == "incomplete")
    updated = vault.update_task(task["file_path"], task["line_number"], "add_reminder", "2026-04-01 08:00")
    assert updated["reminder_time"] == "2026-04-01 08:00"


def test_update_add_reminder_persisted(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = next(t for t in tasks if t["status"] == "incomplete")
    vault.update_task(task["file_path"], task["line_number"], "add_reminder", "2026-04-01 08:00")
    refreshed = vault.get_all_tasks()
    found = next(
        t for t in refreshed
        if t["file_path"] == task["file_path"] and t["line_number"] == task["line_number"]
    )
    assert found["reminder_time"] == "2026-04-01 08:00"
    # ⏰ must appear before 📅 in the raw line
    lines = (vault.vault_path / task["file_path"]).read_text(encoding="utf-8").splitlines()
    raw = lines[task["line_number"] - 1]
    assert "⏰ 2026-04-01 08:00" in raw


def test_update_add_reminder_date_only(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = next(t for t in tasks if t["status"] == "incomplete")
    updated = vault.update_task(task["file_path"], task["line_number"], "add_reminder", "2026-04-01")
    assert updated["reminder_time"] == "2026-04-01"


def test_update_remove_reminder(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = next(t for t in tasks if t["status"] == "incomplete")
    # First add a reminder, then remove it
    vault.update_task(task["file_path"], task["line_number"], "add_reminder", "2026-04-01 08:00")
    updated = vault.update_task(task["file_path"], task["line_number"], "remove_reminder")
    assert updated["reminder_time"] == ""


def test_update_remove_reminder_persisted(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = next(t for t in tasks if t["status"] == "incomplete")
    vault.update_task(task["file_path"], task["line_number"], "add_reminder", "2026-04-01 08:00")
    vault.update_task(task["file_path"], task["line_number"], "remove_reminder")
    refreshed = vault.get_all_tasks()
    found = next(
        t for t in refreshed
        if t["file_path"] == task["file_path"] and t["line_number"] == task["line_number"]
    )
    assert found["reminder_time"] == ""
    lines = (vault.vault_path / task["file_path"]).read_text(encoding="utf-8").splitlines()
    raw = lines[task["line_number"] - 1]
    assert "⏰" not in raw


# ---------------------------------------------------------------------------
# delete_task — dry_run
# ---------------------------------------------------------------------------


def test_delete_task_dry_run(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = next(t for t in tasks if t["status"] == "incomplete")
    result = vault.delete_task(task["file_path"], task["line_number"], dry_run=True)
    assert result["dry_run"] is True
    assert result["line_number"] == task["line_number"]
    # File must be unchanged
    after = vault.get_all_tasks()
    assert len(after) == len(tasks)


def test_delete_task_dry_run_returns_task_content(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = next(t for t in tasks if t["status"] == "incomplete")
    result = vault.delete_task(task["file_path"], task["line_number"], dry_run=True)
    assert task["description"] in result["would_delete"]


# ---------------------------------------------------------------------------
# delete_task — actual deletion
# ---------------------------------------------------------------------------


def test_delete_task_removes_line(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = next(t for t in tasks if t["status"] == "incomplete")
    vault.delete_task(task["file_path"], task["line_number"])
    after = vault.get_all_tasks()
    # One fewer task should exist overall
    assert len(after) == len(tasks) - 1
    # The specific task description should no longer exist in that file
    descriptions_in_file = {
        t["description"] for t in after if t["file_path"] == task["file_path"]
    }
    assert task["description"] not in descriptions_in_file


def test_delete_task_returns_confirmation(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = next(t for t in tasks if t["status"] == "incomplete")
    result = vault.delete_task(task["file_path"], task["line_number"])
    assert "deleted" in result
    assert result["file"] == task["file_path"]
    assert result["line_number"] == task["line_number"]


def test_delete_task_no_consecutive_blank_lines(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = next(t for t in tasks if t["status"] == "incomplete")
    vault.delete_task(task["file_path"], task["line_number"])
    content = (vault.vault_path / task["file_path"]).read_text(encoding="utf-8")
    assert "\n\n\n" not in content


# ---------------------------------------------------------------------------
# delete_task — error cases
# ---------------------------------------------------------------------------


def test_delete_task_invalid_line_number(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = tasks[0]
    with pytest.raises(ValueError, match="out of range"):
        vault.delete_task(task["file_path"], 99999)


def test_delete_task_non_task_line(vault: VaultManager):
    with pytest.raises(ValueError, match="not a task line"):
        vault.delete_task("Projects/work.md", 1)  # heading line


def test_delete_task_path_traversal(vault: VaultManager):
    with pytest.raises(ValueError, match="Path outside vault"):
        vault.delete_task("../../etc/passwd", 1)


# ---------------------------------------------------------------------------
# bulk_update_tasks — dry_run
# ---------------------------------------------------------------------------


def test_bulk_update_dry_run(vault: VaultManager):
    tasks = vault.get_all_tasks()
    incomplete = [t for t in tasks if t["status"] == "incomplete"][:2]
    ids = [t["id"] for t in incomplete]
    result = vault.bulk_update_tasks(ids, "mark_done", dry_run=True)
    assert result["dry_run"] is True
    assert result["would_update_count"] == 2
    # No changes written
    after = vault.get_all_tasks()
    assert sum(1 for t in after if t["status"] == "incomplete") == sum(
        1 for t in tasks if t["status"] == "incomplete"
    )


# ---------------------------------------------------------------------------
# bulk_update_tasks — actual updates
# ---------------------------------------------------------------------------


def test_bulk_update_mark_done(vault: VaultManager):
    tasks = vault.get_all_tasks()
    incomplete = [t for t in tasks if t["status"] == "incomplete"]
    ids = [t["id"] for t in incomplete]
    result = vault.bulk_update_tasks(ids, "mark_done")
    assert result["updated_count"] == len(incomplete)
    assert result["failed_count"] == 0
    after = vault.get_all_tasks()
    assert all(t["status"] == "complete" for t in after)


def test_bulk_update_multiple_files(vault: VaultManager):
    tasks = vault.get_all_tasks()
    incomplete = [t for t in tasks if t["status"] == "incomplete"]
    ids = [t["id"] for t in incomplete]
    result = vault.bulk_update_tasks(ids, "mark_done")
    assert result["updated_count"] > 0


def test_bulk_update_add_tag(vault: VaultManager):
    tasks = vault.get_all_tasks()
    ids = [t["id"] for t in tasks if "bulk-tag" not in t["tags"]][:3]
    vault.bulk_update_tasks(ids, "add_tag", "bulk-tag")
    after = vault.get_all_tasks()
    updated = [t for t in after if t["id"] in ids]
    for t in updated:
        assert "bulk-tag" in t["tags"]


def test_bulk_update_empty_task_ids(vault: VaultManager):
    result = vault.bulk_update_tasks([], "mark_done")
    assert "message" in result


def test_bulk_update_handles_missing_file(vault: VaultManager):
    result = vault.bulk_update_tasks(["nonexistent/file.md:1"], "mark_done")
    assert result["failed_count"] == 1
    assert result["failed"][0]["reason"] == "file not found"


def test_bulk_update_handles_line_out_of_range(vault: VaultManager):
    tasks = vault.get_all_tasks()
    task = tasks[0]
    result = vault.bulk_update_tasks([f"{task['file_path']}:99999"], "mark_done")
    assert result["failed_count"] == 1


def test_bulk_update_handles_non_task_line(vault: VaultManager):
    result = vault.bulk_update_tasks(["Projects/work.md:1"], "mark_done")
    assert result["failed_count"] == 1
    assert result["failed"][0]["reason"] == "not a task line"


# ---------------------------------------------------------------------------
# _group_by_file
# ---------------------------------------------------------------------------


def test_group_by_file_descending_order():
    task_ids = [
        "Projects/work.md:5",
        "Projects/work.md:10",
        "Journal/2026-03-14.md:7",
    ]
    grouped = VaultManager._group_by_file(task_ids)
    assert grouped["Projects/work.md"] == [10, 5]
    assert grouped["Journal/2026-03-14.md"] == [7]


def test_group_by_file_ignores_malformed():
    grouped = VaultManager._group_by_file(["bad-id-no-colon"])
    assert len(grouped) == 0


# ---------------------------------------------------------------------------
# _clean_blank_lines
# ---------------------------------------------------------------------------


def test_clean_blank_lines_removes_consecutive():
    lines = ["a", "", "", "b"]
    result = VaultManager._clean_blank_lines(lines)
    assert result == ["a", "", "b"]


def test_clean_blank_lines_keeps_single():
    lines = ["a", "", "b"]
    result = VaultManager._clean_blank_lines(lines)
    assert result == ["a", "", "b"]


# ---------------------------------------------------------------------------
# create_task — inline metadata in description (tag before due date)
# ---------------------------------------------------------------------------


def test_create_task_description_with_embedded_tag_and_due(tmp_path: Path):
    """create_task cleans embedded #tag and 📅 date from the description."""
    v = VaultManager(tmp_path)
    task = v.create_task(
        description="compare llms? #micro-mng-todo 📅 2026-03-21",
        target="inbox",
    )
    assert task["description"] == "compare llms?"
    assert "micro-mng-todo" in task["tags"]
    assert task["due_date"] == "2026-03-21"


def test_create_task_explicit_due_overrides_embedded(tmp_path: Path):
    """Explicit due_date parameter takes precedence over embedded date."""
    v = VaultManager(tmp_path)
    task = v.create_task(
        description="compare llms? #micro-mng-todo 📅 2026-03-21",
        due_date="2026-03-25",
        target="inbox",
    )
    assert task["due_date"] == "2026-03-25"
    assert "micro-mng-todo" in task["tags"]


def test_create_task_explicit_tag_merged_with_embedded(tmp_path: Path):
    """Explicit tag and embedded tag are both stored (deduplicated)."""
    v = VaultManager(tmp_path)
    task = v.create_task(
        description="compare llms? #micro-mng-todo 📅 2026-03-21",
        tag="work",
        target="inbox",
    )
    assert "micro-mng-todo" in task["tags"]
    assert "work" in task["tags"]


def test_create_task_embedded_tag_written_correctly(tmp_path: Path):
    """The stored file line must reflect the extracted metadata."""
    v = VaultManager(tmp_path)
    task = v.create_task(
        description="compare llms? #micro-mng-todo 📅 2026-03-21",
        target="inbox",
    )
    # Read the written line back and re-parse to confirm it round-trips cleanly.
    lines = (tmp_path / "Inbox.md").read_text(encoding="utf-8").splitlines()
    written_line = lines[task["line_number"] - 1]
    from obsidian_tasks_mcp.parser import parse_task_line
    reparsed = parse_task_line(written_line, "Inbox.md", task["line_number"])
    assert reparsed is not None
    assert reparsed["description"] == "compare llms?"
    assert "micro-mng-todo" in reparsed["tags"]
    assert reparsed["due_date"] == "2026-03-21"


# ---------------------------------------------------------------------------
# update_description — inline metadata in new value (tag before due date)
# ---------------------------------------------------------------------------


def test_update_description_with_embedded_tag_and_due(vault: VaultManager):
    """update_description extracts #tag and 📅 date from the new description."""
    tasks = vault.get_all_tasks()
    target = next(t for t in tasks if t["status"] == "incomplete")
    task = vault.update_task(
        target["file_path"],
        target["line_number"],
        "update_description",
        "new task text #newwork 📅 2026-05-01",
    )
    assert task["description"] == "new task text"
    assert "newwork" in task["tags"]
    assert task["due_date"] == "2026-05-01"


def test_update_description_embedded_due_not_duplicated(vault: VaultManager):
    """Embedding a due date in update_description must not produce duplicate 📅 tokens."""
    tasks = vault.get_all_tasks()
    # Pick a task that already has a due date so we can verify it gets replaced.
    target = next((t for t in tasks if t["status"] == "incomplete" and t["due_date"]), None)
    if target is None:
        pytest.skip("No incomplete task with due date in sample vault")

    task = vault.update_task(
        target["file_path"],
        target["line_number"],
        "update_description",
        "replaced description #qtag 📅 2026-09-01",
    )
    # Re-read the written line to confirm no duplicate 📅.
    lines = (vault.vault_path / target["file_path"]).read_text(encoding="utf-8").splitlines()
    written = lines[target["line_number"] - 1]
    assert written.count("📅") == 1
    assert task["due_date"] == "2026-09-01"
    assert "qtag" in task["tags"]
