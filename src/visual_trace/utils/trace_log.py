import json
import os
from pathlib import Path
from typing import Any

ENV_VAR = "VISUAL_TRACE_LOG"

REPR_LIMIT = 160


def safe_repr(value: Any, limit: int = REPR_LIMIT) -> str:
    """Repr a traced value without ever raising or triggering animations.

    Builtin containers repr themselves through their C implementation, so this
    does not call the overridden ``items``/``keys``/``values`` on ``Dict`` and
    therefore cannot push spurious animations onto its queue.
    """
    try:
        text = repr(value)
    except Exception as exc:  # a user object with a broken __repr__
        text = f"<unreprable {type(value).__name__}: {exc}>"
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text


class TraceLog:
    """JSONL sidecar recording one entry per animated trace step."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("w")
        self.records: list[dict] = []

    def emit(self, **record: Any) -> None:
        self.records.append(record)
        self._fh.write(json.dumps(record, default=str) + "\n")
        self._fh.flush()

    def close(self) -> None:
        if not self._fh.closed:
            self._fh.close()


def open_log(path: str | Path | None = None) -> TraceLog | None:
    """Return a log if one was requested, else ``None``.

    Renders are untouched unless ``VISUAL_TRACE_LOG`` is set.
    """
    path = path or os.environ.get(ENV_VAR)
    if not path:
        return None
    return TraceLog(path)
