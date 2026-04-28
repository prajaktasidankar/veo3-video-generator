"""Gradio UI for Veo 3.1 image-to-video generation."""

import gradio as gr

from models.veo_client import generate_video_veo


def run_generation(
    source_image: str | None,
    motion_prompt: str,
    aspect_ratio: str,
    duration_seconds: float,
    include_audio: bool,
    progress: gr.Progress = gr.Progress(),
) -> tuple[str | None, str]:
    def on_progress(message: str) -> None:
        progress(0, desc=message)

    if not source_image or not str(source_image).strip():
        return None, "**Error:** Upload a **source image** first — video is generated from your image."

    try:
        path = generate_video_veo(
            prompt=motion_prompt or "",
            aspect_ratio=aspect_ratio,
            duration_seconds=int(duration_seconds),
            include_audio=include_audio,
            image_path=source_image,
            on_progress=on_progress,
        )
        return path, f"Ready. File: `{path}`"
    except Exception as exc:
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
        include_audio = gr.Checkbox(label="Include audio", value=True)

    generate_btn = gr.Button("Generate video", variant="primary")

    status = gr.Markdown("")
    video = gr.Video(label="Generated video")

    generate_btn.click(
        fn=run_generation,
        inputs=[source_image, motion_prompt, aspect, duration, include_audio],
        outputs=[video, status],
        show_progress="full",
    )


if __name__ == "__main__":
    demo.queue().launch()
