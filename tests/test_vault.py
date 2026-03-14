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
    required = {"id", "description", "status", "tags", "due_date", "priority", "file_path", "line_number"}
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
