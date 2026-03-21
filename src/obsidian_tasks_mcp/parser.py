"""Parser for Obsidian Tasks plugin markdown format.

Handles the emoji-based syntax used by the Obsidian Tasks plugin:
  - [ ] Description 🔺 📅 2026-03-15 #tag
  - [x] Done task ✅ 2026-03-14

Custom / Obsidian-style checkbox characters are fully supported.  Any
character other than ``x`` / ``X`` is treated as *incomplete*, so statuses
such as ``[d]`` (doing), ``[!]`` (blocked), or ``[-]`` (cancelled) all appear
in incomplete/pending task lists.

Also handles the Reminder plugin ⏰ syntax:
  - [ ] Task ⏰ 2026-03-15        (reminder on that date at default time)
  - [ ] Task ⏰ 2026-03-15 10:00  (reminder at specific time)
  - [ ] Task 🔺 ⏰ 2026-03-15 09:00 📅 2026-03-15 #tag
"""

import re
from typing import Optional

# Match a task line: optional indent, dash, checkbox (any single char), content
TASK_LINE_PATTERN = re.compile(r"^(\s*)-\s+\[(.)\]\s+(.+)$")

# Obsidian Tasks plugin emoji patterns
DUE_DATE_PATTERN = re.compile(r"📅\s*(\d{4}-\d{2}-\d{2})")
DONE_DATE_PATTERN = re.compile(r"✅\s*(\d{4}-\d{2}-\d{2})")
SCHEDULED_DATE_PATTERN = re.compile(r"⏳\s*(\d{4}-\d{2}-\d{2})")

# Reminder plugin ⏰ pattern: date only, or date + HH:mm time
REMINDER_PATTERN = re.compile(r"⏰\s*(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2})?)")

# Tags: #word-with-hyphens or #word/with/slashes, not starting with digit
TAG_PATTERN = re.compile(r"(?<![&\w])#([A-Za-z_][A-Za-z0-9_/\-]*)")

# Wikilinks: [[link text]] or [[link|alias]]
WIKILINK_PATTERN = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")

# Priority emoji mappings (Obsidian Tasks plugin standard)
# Each entry: (tuple of emoji variants, priority name)
_PRIORITY_ENTRIES: list[tuple[tuple[str, ...], str]] = [
    (("🔺",), "highest"),
    (("⬆️", "⬆"),  "high"),
    (("🔼",), "medium"),
    (("🔽",), "low"),
    (("⬇️", "⬇"),  "lowest"),
]

# Build lookup maps
EMOJI_TO_PRIORITY: dict[str, str] = {}
for _emojis, _name in _PRIORITY_ENTRIES:
    for _e in _emojis:
        EMOJI_TO_PRIORITY[_e] = _name

# Use the first (canonical) emoji for each priority when formatting
PRIORITY_TO_EMOJI: dict[str, str] = {
    name: emojis[0] for emojis, name in _PRIORITY_ENTRIES
}
PRIORITY_TO_EMOJI["none"] = ""


def is_task_line(line: str) -> bool:
    """Return True if the line is an Obsidian task line."""
    return TASK_LINE_PATTERN.match(line) is not None


def parse_task_line(
    line: str, file_path: str = "", line_number: int = 0
) -> Optional[dict]:
    """Parse an Obsidian Tasks plugin task line into a structured dict.

    Returns None if the line is not a task line.

    The returned dict has keys:
        id, description, status, status_char, tags, due_date, done_date,
        reminder_time, priority, file_path, line_number

    ``status_char`` is the raw single character found inside the checkbox
    brackets (e.g. ``" "``, ``"x"``, ``"d"``, ``"!"``, ``"-"``).  It is
    preserved so that ``format_task_line`` can round-trip custom Obsidian
    checkbox styles without losing the original character.
    """
    match = TASK_LINE_PATTERN.match(line)
    if not match:
        return None

    _indent, status_char, content = match.groups()
    status = "complete" if status_char.lower() == "x" else "incomplete"

    # Extract due date
    due_match = DUE_DATE_PATTERN.search(content)
    due_date = due_match.group(1) if due_match else ""

    # Extract done date
    done_match = DONE_DATE_PATTERN.search(content)
    done_date = done_match.group(1) if done_match else ""

    # Extract reminder time (⏰ YYYY-MM-DD or ⏰ YYYY-MM-DD HH:mm)
    reminder_match = REMINDER_PATTERN.search(content)
    reminder_time = reminder_match.group(1).strip() if reminder_match else ""

    # Extract priority (first matching emoji wins)
    priority = "none"
    for emoji, name in EMOJI_TO_PRIORITY.items():
        if emoji in content:
            priority = name
            break

    # Extract inline tags
    tags = TAG_PATTERN.findall(content)

    # Extract wikilinks [[target]] or [[target|alias]]
    wikilinks = WIKILINK_PATTERN.findall(content)

    # Build description: strip all known emoji markers and tags
    description = content
    description = DUE_DATE_PATTERN.sub("", description)
    description = DONE_DATE_PATTERN.sub("", description)
    description = SCHEDULED_DATE_PATTERN.sub("", description)
    description = REMINDER_PATTERN.sub("", description)
    # Strip the ⏰ emoji itself (in case it remained after regex sub)
    description = description.replace("⏰", "")
    for emoji in EMOJI_TO_PRIORITY:
        description = description.replace(emoji, "")
    description = TAG_PATTERN.sub("", description)
    description = description.strip()

    return {
        "id": f"{file_path}:{line_number}",
        "description": description,
        "status": status,
        "status_char": status_char,
        "tags": tags,
        "wikilinks": wikilinks,
        "due_date": due_date,
        "done_date": done_date,
        "reminder_time": reminder_time,
        "priority": priority,
        "file_path": file_path,
        "line_number": line_number,
    }


def format_task_line(task: dict) -> str:
    """Serialise a task dict back to an Obsidian Tasks plugin markdown line.

    Output order: - [status] description [priority] [⏰ reminder] [📅 due] [✅ done] [#tags]

    The ⏰ reminder is placed immediately before 📅 due date (if both are present)
    to comply with the Reminder plugin's parsing requirements.
    """
    if task.get("status") == "complete":
        status_char = "x"
    else:
        # Preserve the original custom checkbox character (e.g. "d", "!", "-").
        # Fall back to a plain space for brand-new tasks that have no stored char.
        status_char = task.get("status_char", " ")
        if status_char.lower() == "x":
            # Guard: "x"/"X" must not appear in an incomplete task's bracket.
            status_char = " "

    parts: list[str] = [f"- [{status_char}]", task.get("description", "").strip()]

    priority = task.get("priority", "none")
    if priority and priority != "none":
        emoji = PRIORITY_TO_EMOJI.get(priority, "")
        if emoji:
            parts.append(emoji)

    reminder_time = task.get("reminder_time", "")
    if reminder_time:
        parts.append(f"⏰ {reminder_time}")

    due_date = task.get("due_date", "")
    if due_date:
        parts.append(f"📅 {due_date}")

    done_date = task.get("done_date", "")
    if done_date:
        parts.append(f"✅ {done_date}")

    for tag in task.get("tags", []):
        if tag:
            parts.append(f"#{tag}")

    return " ".join(p for p in parts if p)
