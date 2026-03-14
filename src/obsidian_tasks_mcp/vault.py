"""Vault traversal, file I/O, and task write operations."""

from datetime import date
from pathlib import Path

from obsidian_tasks_mcp.parser import format_task_line, parse_task_line


class VaultManager:
    """Manages reading and writing tasks in an Obsidian vault directory."""

    def __init__(self, vault_path: Path | str) -> None:
        self.vault_path = Path(vault_path) if vault_path else Path(".")

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_all_tasks(self) -> list[dict]:
        """Walk every Markdown file in the vault and return all task dicts."""
        tasks: list[dict] = []

        if not self.vault_path.exists() or not self.vault_path.is_dir():
            return tasks

        for md_file in sorted(self.vault_path.rglob("*.md")):
            rel_path = md_file.relative_to(self.vault_path).as_posix()
            try:
                lines = md_file.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue

            for i, line in enumerate(lines, start=1):
                task = parse_task_line(line, rel_path, i)
                if task is not None:
                    tasks.append(task)

        return tasks

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _full_path(self, rel_path: str) -> Path:
        return self.vault_path / rel_path

    def _read_lines(self, rel_path: str) -> list[str]:
        full = self._full_path(rel_path)
        if not full.exists():
            raise FileNotFoundError(f"File not found in vault: {rel_path}")
        return full.read_text(encoding="utf-8").splitlines()

    def _write_lines(self, rel_path: str, lines: list[str]) -> None:
        full = self._full_path(rel_path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ------------------------------------------------------------------
    # Update operation
    # ------------------------------------------------------------------

    def update_task(
        self, file_path: str, line_number: int, operation: str, value: str = ""
    ) -> dict:
        """Apply *operation* to the task at *line_number* in *file_path*.

        ``line_number`` is 1-based (as returned by ``list_tasks``).

        Returns the updated task dict.

        Supported operations:
            mark_done           — set status=complete, set done_date=today
            mark_undone         — set status=incomplete, clear done_date
            add_due_date        — set due_date=value (YYYY-MM-DD)
            reschedule          — replace due_date with value
            add_tag             — append tag (value, with or without leading #)
            remove_tag          — remove tag (value, with or without leading #)
            update_description  — replace task description with value
        """
        lines = self._read_lines(file_path)
        if line_number < 1 or line_number > len(lines):
            raise ValueError(
                f"line_number {line_number} is out of range for {file_path} "
                f"({len(lines)} lines)"
            )

        raw_line = lines[line_number - 1]
        task = parse_task_line(raw_line, file_path, line_number)
        if task is None:
            raise ValueError(
                f"Line {line_number} in {file_path!r} is not a task line: {raw_line!r}"
            )

        today = date.today().isoformat()

        if operation == "mark_done":
            task["status"] = "complete"
            task["done_date"] = today
        elif operation == "mark_undone":
            task["status"] = "incomplete"
            task["done_date"] = ""
        elif operation in ("add_due_date", "reschedule"):
            task["due_date"] = value
        elif operation == "add_tag":
            tag = value.lstrip("#")
            if tag and tag not in task["tags"]:
                task["tags"].append(tag)
        elif operation == "remove_tag":
            tag = value.lstrip("#")
            task["tags"] = [t for t in task["tags"] if t != tag]
        elif operation == "update_description":
            task["description"] = value
        else:
            raise ValueError(f"Unknown operation: {operation!r}")

        new_line = format_task_line(task)
        lines[line_number - 1] = new_line
        self._write_lines(file_path, lines)

        return task

    # ------------------------------------------------------------------
    # Create operation
    # ------------------------------------------------------------------

    def create_task(
        self,
        description: str,
        tag: str = "",
        due_date: str = "",
        priority: str = "none",
        target: str = "daily_note",
        file_path: str = "",
    ) -> dict:
        """Create a new task and append it to the target file.

        Targets:
            daily_note  — Journal/<YYYY-MM-DD>.md (created if missing)
            inbox       — Inbox.md at vault root   (created if missing)
            file        — the path given in *file_path*

        Returns the created task dict (including id, file_path, line_number).
        """
        task: dict = {
            "description": description,
            "status": "incomplete",
            "tags": [tag.lstrip("#")] if tag else [],
            "due_date": due_date,
            "done_date": "",
            "priority": priority,
        }

        task_line = format_task_line(task)

        if target == "daily_note":
            today = date.today().strftime("%Y-%m-%d")
            rel_path = f"Journal/{today}.md"
        elif target == "inbox":
            rel_path = "Inbox.md"
        elif target == "file":
            if not file_path:
                raise ValueError("file_path must be provided when target='file'")
            rel_path = file_path
        else:
            raise ValueError(f"Unknown target: {target!r}")

        full = self._full_path(rel_path)
        full.parent.mkdir(parents=True, exist_ok=True)

        if full.exists():
            existing = full.read_text(encoding="utf-8")
            content = existing if existing.endswith("\n") else existing + "\n"
            content += task_line + "\n"
        else:
            content = task_line + "\n"

        full.write_text(content, encoding="utf-8")

        line_number = len(content.splitlines())
        task["file_path"] = rel_path
        task["line_number"] = line_number
        task["id"] = f"{rel_path}:{line_number}"

        return task
