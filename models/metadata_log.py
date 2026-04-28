"""Write per-run JSON metadata next to generated videos (or failure logs)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_LOG_DIR = _PROJECT_ROOT / "temp_outputs"


def save_metadata(video_path: str | Path | None, metadata: dict[str, Any]) -> Path:
    """Write ``metadata`` to a JSON file next to the video (same stem) or a failure log.

    - If ``video_path`` is set, writes ``<stem>.json`` beside the video.
    - If ``video_path`` is None (failed run with no video file), writes
      ``temp_outputs/veo_failed_<utc_timestamp>.json``.
    """
    md = dict(metadata)
    md.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

    if video_path is not None:
        vp = Path(video_path)
        vp.parent.mkdir(parents=True, exist_ok=True)
        out = vp.with_suffix(".json")
    else:
        _DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        stem = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out = _DEFAULT_LOG_DIR / f"veo_failed_{stem}.json"

    out.write_text(json.dumps(md, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out.resolve()
