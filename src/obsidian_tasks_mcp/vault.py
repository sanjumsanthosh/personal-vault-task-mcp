"""Vault traversal, file I/O, and task write operations."""

from collections import defaultdict
from datetime import date
from pathlib import Path

from obsidian_tasks_mcp.parser import format_task_line, is_task_line, parse_task_line


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

    def _is_safe_path(self, rel_path: str) -> bool:
        """Prevent path traversal outside the vault directory."""
        try:
            (self.vault_path / rel_path).resolve().relative_to(self.vault_path.resolve())
            return True
        except ValueError:
            return False

    def _full_path(self, rel_path: str) -> Path:
        return self.vault_path / rel_path

    def _read_lines(self, rel_path: str) -> list[str]:
        full = self._full_path(rel_path)
        if not full.exists():
            raise FileNotFoundError(f"File not found in vault: {rel_path}")
        return full.read_text(encoding="utf-8").splitlines()

    def _write_lines(self, rel_path: str, lines: list[str]) -> None:
        """Write lines back atomically: write to .tmp then rename to avoid corruption."""
        full = self._full_path(rel_path)
        full.parent.mkdir(parents=True, exist_ok=True)
        tmp = full.with_name(full.name + ".tmp")
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        tmp.replace(full)

    @staticmethod
    def _clean_blank_lines(lines: list[str]) -> list[str]:
        """Remove consecutive blank lines, keeping at most one in a row."""
        result: list[str] = []
        prev_blank = False
        for line in lines:
            is_blank = line.strip() == ""
            if is_blank and prev_blank:
                continue
            result.append(line)
            prev_blank = is_blank
        return result

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
            mark_undone         — set status=incomplete (plain [ ]), clear done_date
            mark_doing          — set status=incomplete with [d] checkbox (in progress)
            add_due_date        — set due_date=value (YYYY-MM-DD)
            reschedule          — replace due_date with value
            add_tag             — append tag (value, with or without leading #)
            remove_tag          — remove tag (value, with or without leading #)
            update_description  — replace task description with value
            add_reminder        — set reminder_time=value (YYYY-MM-DD or YYYY-MM-DD HH:mm)
            remove_reminder     — clear reminder_time
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
            task["status_char"] = " "
            task["done_date"] = ""
        elif operation == "mark_doing":
            task["status"] = "incomplete"
            task["status_char"] = "d"
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
        elif operation == "add_reminder":
            task["reminder_time"] = value
        elif operation == "remove_reminder":
            task["reminder_time"] = ""
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
        reminder_time: str = "",
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
            "reminder_time": reminder_time,
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

    # ------------------------------------------------------------------
    # Delete operation
    # ------------------------------------------------------------------

    def delete_task(
        self, file_path: str, line_number: int, dry_run: bool = False
    ) -> dict:
        """Delete a task line from a vault file.

        ``line_number`` is 1-based (as returned by ``list_tasks``).

        Pass ``dry_run=True`` to preview what would be deleted without
        making any changes.

        Returns a confirmation dict (or a preview dict when dry_run=True).
        """
        if not self._is_safe_path(file_path):
            raise ValueError(f"Path outside vault: {file_path}")

        lines = self._read_lines(file_path)

        if line_number < 1 or line_number > len(lines):
            raise ValueError(
                f"line_number {line_number} is out of range for {file_path} "
                f"({len(lines)} lines)"
            )

        target_line = lines[line_number - 1]

        if not is_task_line(target_line):
            raise ValueError(
                f"Line {line_number} in {file_path!r} is not a task line: {target_line!r}"
            )

        if dry_run:
            return {
                "dry_run": True,
                "would_delete": target_line.strip(),
                "file": file_path,
                "line_number": line_number,
            }

        lines.pop(line_number - 1)
        lines = self._clean_blank_lines(lines)
        self._write_lines(file_path, lines)

        return {
            "deleted": target_line.strip(),
            "file": file_path,
            "line_number": line_number,
        }

    # ------------------------------------------------------------------
    # Bulk update helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _group_by_file(task_ids: list[str]) -> dict[str, list[int]]:
        """Group task IDs by file path → {filepath: [line_numbers sorted desc]}.

        Descending sort is critical: editing from bottom-up preserves the
        line numbers of all lines above each edit.
        """
        groups: dict[str, list[int]] = defaultdict(list)
        for tid in task_ids:
            parts = tid.rsplit(":", 1)
            if len(parts) == 2:
                filepath, lineno_str = parts
                try:
                    groups[filepath].append(int(lineno_str))
                except ValueError:
                    continue
        return {fp: sorted(lns, reverse=True) for fp, lns in groups.items()}

    @staticmethod
    def _apply_operation(
        line: str, operation: str, value: str,
        file_path: str = "", line_number: int = 0,
    ) -> str:
        """Apply *operation* to a raw task line string and return the updated line."""
        task = parse_task_line(line, file_path, line_number)
        if task is None:
            return line

        today = date.today().isoformat()

        if operation == "mark_done":
            task["status"] = "complete"
            task["done_date"] = today
        elif operation == "mark_undone":
            task["status"] = "incomplete"
            task["status_char"] = " "
            task["done_date"] = ""
        elif operation == "mark_doing":
            task["status"] = "incomplete"
            task["status_char"] = "d"
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
        elif operation == "add_reminder":
            task["reminder_time"] = value
        elif operation == "remove_reminder":
            task["reminder_time"] = ""
        else:
            raise ValueError(f"Unknown operation: {operation!r}")

        return format_task_line(task)

    # ------------------------------------------------------------------
    # Bulk update operation
    # ------------------------------------------------------------------

    def bulk_update_tasks(
        self,
        task_ids: list[str],
        operation: str,
        value: str = "",
        dry_run: bool = False,
    ) -> dict:
        """Apply *operation* to every task in *task_ids* in a single pass.

        Tasks are grouped by file and edits are applied bottom-up (descending
        line numbers) so that earlier line numbers remain valid after each edit.

        Pass ``dry_run=True`` to preview changes without writing to disk.
        """
        if not task_ids:
            return {"message": "No tasks provided — nothing to update"}

        if dry_run:
            return {
                "dry_run": True,
                "would_update_count": len(task_ids),
                "operation": operation,
                "task_ids": task_ids,
            }

        grouped = self._group_by_file(task_ids)
        results: dict = {"updated": [], "failed": []}

        for file_path, line_numbers in grouped.items():
            try:
                lines = self._read_lines(file_path)
            except FileNotFoundError:
                for ln in line_numbers:
                    results["failed"].append(
                        {"id": f"{file_path}:{ln}", "reason": "file not found"}
                    )
                continue

            changed = False
            for ln in line_numbers:  # already sorted descending
                if ln < 1 or ln > len(lines):
                    results["failed"].append(
                        {"id": f"{file_path}:{ln}", "reason": "line out of range"}
                    )
                    continue

                original = lines[ln - 1]
                if not is_task_line(original):
                    results["failed"].append(
                        {"id": f"{file_path}:{ln}", "reason": "not a task line"}
                    )
                    continue

                try:
                    updated = self._apply_operation(original, operation, value, file_path, ln)
                except ValueError as exc:
                    results["failed"].append(
                        {"id": f"{file_path}:{ln}", "reason": str(exc)}
                    )
                    continue

                if updated != original:
                    lines[ln - 1] = updated
                    changed = True
                results["updated"].append(f"{file_path}:{ln}")

            if changed:
                self._write_lines(file_path, lines)

        results["updated_count"] = len(results["updated"])
        results["failed_count"] = len(results["failed"])
        return results
