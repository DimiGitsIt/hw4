"""Append-only audit trail of what the agent does on each chat request.

Writes to output/audit_trail.json (project-level, outside backend/) as a single JSON
array. Never wipes or truncates — every write reads the existing array, appends, and
writes the whole array back via a temp-file-then-rename (atomic on the same filesystem),
so a crash mid-write can't leave a half-written file. A process-wide lock serializes
writes so two concurrent requests can't interleave and corrupt the file.

Entries intentionally carry very little: a tool name, a short args/result summary, and
(on the request's final entry only) a stop reason. No passwords, hashes, API keys, or
full chat message text ever go in here — for a logged-in user we record at most their
numeric user_id, never their name or email.
"""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
AUDIT_PATH = PROJECT_ROOT / "output" / "audit_trail.json"

MAX_FIELD_LENGTH = 200

_lock = threading.Lock()


def _shorten(value: Any) -> Any:
    """Keep audit entries small — truncate long strings, cap collection sizes."""
    if isinstance(value, str):
        return value if len(value) <= MAX_FIELD_LENGTH else value[: MAX_FIELD_LENGTH - 3] + "..."
    if isinstance(value, dict):
        return {k: _shorten(v) for k, v in list(value.items())[:10]}
    if isinstance(value, (list, tuple)):
        shortened = [_shorten(v) for v in value[:5]]
        if len(value) > 5:
            shortened.append(f"...(+{len(value) - 5} more)")
        return shortened
    return value


def append_entry(
    *,
    request_id: str,
    tool: str | None,
    args: dict | None = None,
    result_summary: str | None = None,
    stop_reason: str | None = None,
    user_id: int | None = None,
) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "user_id": user_id,
        "tool": tool,
        "args": _shorten(args) if args else {},
        "result_summary": _shorten(result_summary) if result_summary else None,
        "stop_reason": stop_reason,
    }

    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        existing = []
        if AUDIT_PATH.exists():
            try:
                existing = json.loads(AUDIT_PATH.read_text(encoding="utf-8") or "[]")
            except json.JSONDecodeError:
                existing = []
        existing.append(entry)

        tmp_path = AUDIT_PATH.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp_path, AUDIT_PATH)
