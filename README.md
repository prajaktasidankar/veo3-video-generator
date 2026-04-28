# Veo 3.1 Image-to-Video Test App

A Gradio-based test harness for experimenting with Google Veo 3.1 image-to-video generation using the `google-genai` Python SDK.

This project is designed for **testing consistency** and iteration speed:
- Upload a source image
- Optionally describe desired motion/camera behavior
- Generate a video clip with Veo 3.1
- Automatically log run metadata to JSON for traceability

---

## Features

- **Image-to-video generation** with `veo-3.1-generate-preview`
- **Gradio UI** for quick manual testing
- **Async operation polling** until generation completes
- **Automatic file upload + readiness polling** for input image
- **Output download** to `temp_outputs/`
- **Per-run metadata logging**:
  - Success: `<video_stem>.json` next to generated `.mp4`
  - Failure: `veo_failed_<timestamp>.json`

---

## Tech Stack

- Python 3.10+ (recommended)
- [`google-genai`](https://pypi.org/project/google-genai/)
- [`gradio`](https://pypi.org/project/gradio/)
- [`python-dotenv`](https://pypi.org/project/python-dotenv/)

---

## Project Structure

```text
Concert demo/
├─ app.py                    # Gradio UI + request orchestration
├─ requirements.txt          # Python dependencies
├─ .env.example              # Environment template (no secrets)
├─ .gitignore                # Ignores env, outputs, caches, venv
├─ models/
│  ├─ __init__.py            # Exports model helpers
│  ├─ veo_client.py          # Veo generation logic (upload, poll, download, metadata save)
│  └─ metadata_log.py        # save_metadata(...) helper for JSON logs
├─ temp_outputs/             # Generated videos and metadata logs
└─ .venv/                    # Local virtual environment (ignored)


#Setup
1) Create and activate a virtual environment

Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

macOS / Linux
python -m venv .venv
source .venv/bin/activate

2) Install dependencies
  -pip install -r requirements.txt

If requirements.txt is not available/complete, install directly:
  - pip install google-genai gradio python-dotenv

3) Configure environment variables
Copy .env.example to .env:

cp .env.example .env
(Windows PowerShell)

copy .env.example .env
Then set your API key in .env:

GOOGLE_API_KEY=your_api_key_here
Never commit .env. It is ignored by .gitignore.

Run the App
python app.py
Gradio will print a local URL (usually http://127.0.0.1:7860) to open in your browser.

How Generation Works
- User uploads a source image in Gradio
- UI calls run_generation(...) in app.py
- generate_video_veo(...) in models/veo_client.py:
     -Validates input
     -Uploads image (client.files.upload)
     -Polls file state until ACTIVE
     -Calls client.models.generate_videos(...) with:
           -model="veo-3.1-generate-preview"
           -source=GenerateVideosSource(image=..., prompt=...)
     -Polls long-running operation until done
     -Downloads video bytes and saves .mp4 in temp_outputs/
     -Writes metadata JSON via save_metadata(...)

#Metadata Logging
 Metadata is always persisted for test tracking.

#Success logs
Saved next to output video with same stem:
  *veo_20260428_123456.mp4
  *veo_20260428_123456.json

Includes:
  - model_id
  - prompt
  - image_input_used
  - settings (duration, aspect_ratio)
  - timestamp

#Failure logs
Saved as:
  - temp_outputs/veo_failed_<timestamp>.json
Includes attempted prompt/settings and error_message.

#UI Inputs
- Source image (required)
- Motion / scene (optional text prompt)
- Aspect ratio (16:9 or 9:16)
- Duration (4, 6, or 8 seconds)

#Outputs:
- Generated video preview
- Status/error text

#Troubleshooting
GOOGLE_API_KEY is not set

Ensure .env exists and contains:
GOOGLE_API_KEY=...


#Upload/file readiness timeout
Large files or network issues can delay file activation. Retry with a smaller image and stable connection.


#Generation error from API
Check:
- API key validity and quota
- Model availability for your account/region
-Prompt/image policy compliance

#No video returned
The SDK operation may complete without usable outputs if filtered/failed upstream; inspect failure JSON in temp_outputs/.

#Notes
- Model currently configured: veo-3.1-generate-preview
- Project is focused on manual testing workflows rather than production deployment
- temp_outputs/ is intentionally ignored by git to avoid committing generated media/logs
