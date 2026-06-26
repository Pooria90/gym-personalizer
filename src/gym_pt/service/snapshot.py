"""Cheap JSON persistence for a single store's state.

`load()` returns the parsed JSON (or a caller-supplied default if the file is
absent); `save()` writes atomically — temp file + ``os.replace`` — so a crash
mid-write can't corrupt the existing snapshot. Single-writer only (no locking,
no transactions); adequate for single-process dev and replaced by a real
database / native Railtracks memory later.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class JsonSnapshot:
    """Atomic load/save of one store's JSON-serializable state to a file."""

    def __init__(self, path: Path | str):
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def load(self, default: Any) -> Any:
        """Return the parsed file contents, or ``default`` if it doesn't exist."""
        if not self._path.exists():
            return default
        return json.loads(self._path.read_text(encoding="utf-8"))

    def save(self, data: Any) -> None:
        """Atomically overwrite the file with ``data`` (JSON-serialized)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_name(self._path.name + ".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(tmp, self._path)  # atomic on the same filesystem
