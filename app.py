"""Gradio UI for Veo 3.1 image-to-video generation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import gradio as gr

from models.metadata_log import save_metadata
from models.veo_client import VEO_MODEL, generate_video_veo


def run_generation(
    source_image: str | None,
    motion_prompt: str,
    aspect_ratio: str,
    duration_seconds: float,
    progress: gr.Progress = gr.Progress(),
) -> tuple[str | None, str]:
    def on_progress(message: str) -> None:
        progress(0, desc=message)

    base_meta: dict[str, Any] = {
        "model_id": VEO_MODEL,
        "prompt": motion_prompt or "",
        "image_input_used": bool(source_image and str(source_image).strip()),
        "settings": {
            "duration": int(duration_seconds),
            "aspect_ratio": aspect_ratio,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if not source_image or not str(source_image).strip():
        err = "Upload a source image first — video is generated from your image."
        save_metadata(None, {**base_meta, "error_message": err})
        return None, f"**Error:** {err}"

    try:
        path = generate_video_veo(
            prompt=motion_prompt or "",
            aspect_ratio=aspect_ratio,
            duration_seconds=int(duration_seconds),
            image_path=source_image,
            on_progress=on_progress,
        )
        return path, f"Ready. File: `{path}`"
    except Exception as exc:
        save_metadata(None, {**base_meta, "error_message": str(exc)})
        return None, f"**Error:** {exc}"


with gr.Blocks(title="Veo 3.1 — image to video") as demo:
    gr.Markdown(
        "# Veo 3.1 (preview) — image to video\n"
        "Upload a **source image**, then optionally describe **motion or camera** "
        "you want. Video is built from your image."
    )

    with gr.Row():
        source_image = gr.Image(
            label="Source image",
            type="filepath",
            sources=["upload"],
        )
    with gr.Row():
        motion_prompt = gr.Textbox(
            label="Motion / scene (optional)",
            lines=4,
            placeholder="e.g. slow zoom in, gentle wind in the trees, person turns toward camera…",
        )
    with gr.Row():
        aspect = gr.Dropdown(
            choices=["16:9", "9:16"],
            value="16:9",
            label="Aspect ratio",
        )
        duration = gr.Slider(
            minimum=4,
            maximum=8,
            step=2,
            value=6,
            label="Duration (seconds)",
        )

    generate_btn = gr.Button("Generate video", variant="primary")

    status = gr.Markdown("")
    video = gr.Video(label="Generated video")

    generate_btn.click(
        fn=run_generation,
        inputs=[source_image, motion_prompt, aspect, duration],
        outputs=[video, status],
        show_progress="full",
    )


if __name__ == "__main__":
    demo.queue().launch()
