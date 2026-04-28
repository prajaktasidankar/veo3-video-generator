"""Gemini API client wrapper for Veo video generation."""

from __future__ import annotations

import mimetypes
import os
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

from models.metadata_log import save_metadata

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TEMP_OUTPUTS = _PROJECT_ROOT / "temp_outputs"
_POLL_INTERVAL_SEC = 8
_FILE_POLL_INTERVAL_SEC = 1.5
_FILE_READY_TIMEOUT_SEC = 120

VEO_MODEL = "veo-3.1-generate-preview"

ProgressCallback = Optional[Callable[[str], None]]


def _load_env() -> None:
    load_dotenv(_PROJECT_ROOT / ".env")


def get_client() -> genai.Client:
    _load_env()
    key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not key:
        raise EnvironmentError(
            "GOOGLE_API_KEY is not set. Copy .env.example to `.env` and add your API key."
        )
    return genai.Client(api_key=key)


def _videos_result(operation: types.GenerateVideosOperation) -> types.GenerateVideosResponse:
    result = operation.result or operation.response
    if result is None:
        raise RuntimeError("Operation finished but contains no result or response.")
    return result


def _require_image_path(image_path: str | None) -> Path:
    if image_path is None:
        raise ValueError("image_path is required for image-to-video.")
    raw = str(image_path).strip()
    if not raw:
        raise ValueError("image_path is required for image-to-video.")
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Source image not found: {path}")
    return path


def _wait_upload_file_active(
    client: genai.Client,
    name: str,
    notify: Callable[[str], None],
) -> types.File:
    deadline = time.monotonic() + _FILE_READY_TIMEOUT_SEC
    while time.monotonic() < deadline:
        current = client.files.get(name=name)
        if current.state == types.FileState.ACTIVE:
            return current
        if current.state == types.FileState.FAILED:
            err = current.error
            detail = err.message if err and err.message else repr(err)
            raise RuntimeError(f"Uploaded source image failed processing: {detail}")
        notify("Waiting for uploaded file to become ready…")
        time.sleep(_FILE_POLL_INTERVAL_SEC)
    raise TimeoutError("Timed out waiting for the uploaded image to become ACTIVE.")


def generate_video_veo(
    prompt: str,
    aspect_ratio: str,
    duration_seconds: int,
    *,
    image_path: str | None = None,
    model: str = VEO_MODEL,
    on_progress: ProgressCallback = None,
) -> str:
    """Generate a video from a source image with Veo (image-to-video).

    Args:
        prompt: Optional motion / scene description (SDK allows image without text).
        aspect_ratio: ``\"16:9\"`` or ``\"9:16\"``.
        duration_seconds: Clip length (e.g. 4, 6, 8).
        image_path: Local path to the source image (required).
        model: Model id (default Veo 3.1 preview).
        on_progress: Optional callback invoked with human-readable status messages.

    Returns:
        Absolute path to the saved ``.mp4`` file. A matching ``<stem>.json`` is
        written next to the MP4 via :func:`save_metadata`.
    """
    if aspect_ratio not in ("16:9", "9:16"):
        raise ValueError('aspect_ratio must be "16:9" or "9:16".')
    if duration_seconds not in (4, 6, 8):
        raise ValueError("duration_seconds must be 4, 6, or 8.")

    def notify(message: str) -> None:
        if on_progress is not None:
            on_progress(message)

    ref_path = _require_image_path(image_path)

    client = get_client()
    _TEMP_OUTPUTS.mkdir(parents=True, exist_ok=True)

    config = types.GenerateVideosConfig(
        aspect_ratio=aspect_ratio,
        duration_seconds=duration_seconds,
    )

    notify("Starting video generation…")

    mime_type, _ = mimetypes.guess_type(str(ref_path))
    upload_config = types.UploadFileConfig(mime_type=mime_type) if mime_type else None
    notify("Uploading source image…")
    uploaded = client.files.upload(
        file=str(ref_path),
        config=upload_config,
    )
    if not uploaded.name:
        raise RuntimeError("Upload did not return a file name.")
    ready = _wait_upload_file_active(client, uploaded.name, notify)

    input_image = types.Image(
        image_bytes=ref_path.read_bytes(),
        mime_type=ready.mime_type or mime_type,
    )
    motion = prompt.strip()
    source = types.GenerateVideosSource(
        image=input_image,
        prompt=motion if motion else None,
    )
    operation = client.models.generate_videos(
        model=model,
        source=source,
        config=config,
    )

    while operation.done is not True:
        time.sleep(_POLL_INTERVAL_SEC)
        notify("Polling operation until video is ready…")
        operation = client.operations.get(operation)

    if operation.error:
        err = operation.error
        raise RuntimeError(f"Video generation failed: {err}")

    result = _videos_result(operation)
    videos = result.generated_videos or []
    if not videos:
        raise RuntimeError("No generated videos returned.")

    generated = videos[0]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = _TEMP_OUTPUTS / f"veo_{ts}.mp4"

    notify("Downloading video…")
    data = client.files.download(file=generated)
    out_path.write_bytes(data)

    notify(f"Saved to {out_path.name}")

    metadata: dict[str, Any] = {
        "model_id": model,
        "prompt": motion,
        "image_input_used": True,
        "settings": {
            "duration": duration_seconds,
            "aspect_ratio": aspect_ratio,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    save_metadata(out_path, metadata)

    return str(out_path.resolve())
