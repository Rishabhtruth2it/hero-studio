"""Hero Studio — local web app for the product_video pipeline.

Runs entirely on the user's machine. API keys are written to a local .env
file next to this project and never sent anywhere except the official
provider (Runway / Kling) they belong to.
"""
import shutil
import uuid
from pathlib import Path

from dotenv import dotenv_values, set_key
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from product_video import config
from . import pipeline_runner as pr

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
STATIC_DIR = Path(__file__).resolve().parent / "static"
UPLOAD_DIR = config.OUTPUT_DIR / "_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Hero Studio")


def _mask(value: str | None) -> str | None:
    return f"•••• {value[-4:]}" if value else None


@app.get("/api/settings")
def get_settings():
    vals = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}
    return {
        "runway": {
            "configured": bool(vals.get("RUNWAYML_API_SECRET")),
            "masked": _mask(vals.get("RUNWAYML_API_SECRET")),
        },
        "kling": {
            "configured": bool(vals.get("KLING_API_KEY")),
            "masked": _mask(vals.get("KLING_API_KEY")),
            "model": vals.get("KLING_MODEL", "kling-v2-5-turbo"),
        },
    }


@app.post("/api/settings")
async def save_settings(payload: dict):
    if not ENV_PATH.exists():
        ENV_PATH.write_text("")

    if payload.get("runway_key"):
        set_key(str(ENV_PATH), "RUNWAYML_API_SECRET", payload["runway_key"])
        config.RUNWAYML_API_SECRET = payload["runway_key"]

    if payload.get("kling_key"):
        set_key(str(ENV_PATH), "KLING_API_KEY", payload["kling_key"])
        config.KLING_API_KEY = payload["kling_key"]

    if payload.get("kling_model"):
        set_key(str(ENV_PATH), "KLING_MODEL", payload["kling_model"])
        config.KLING_MODEL = payload["kling_model"]

    return {"ok": True}


@app.post("/api/jobs")
async def create_job(
    file: UploadFile = File(...),
    motion_prompt: str = Form(...),
    provider: str = Form("runway"),
    caption: str = Form(""),
    enhance_scene: bool = Form(False),
    scene_prompt: str = Form(""),
    quantize: int = Form(4),
):
    job_id = pr.new_job_id()
    suffix = Path(file.filename or "upload.jpg").suffix or ".jpg"
    dest = UPLOAD_DIR / f"{job_id}{suffix}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    if provider == "runway" and not config.RUNWAYML_API_SECRET:
        return JSONResponse({"error": "No Runway API key configured. Add one in Settings first."}, status_code=400)
    if provider == "kling" and not config.KLING_API_KEY:
        return JSONResponse({"error": "No Kling API key configured. Add one in Settings first."}, status_code=400)

    pr.create_job(
        job_id,
        str(dest),
        motion_prompt,
        provider,
        caption or None,
        enhance_scene,
        scene_prompt or None,
        quantize,
    )
    return {"job_id": job_id}


@app.get("/api/jobs")
def list_jobs():
    jobs = sorted(pr.JOBS.values(), key=lambda j: -j.created_at)
    return [_job_payload(j) for j in jobs]


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = pr.JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not found"}, status_code=404)
    return _job_payload(job)


@app.get("/api/jobs/{job_id}/video")
def job_video(job_id: str):
    job = pr.JOBS.get(job_id)
    if not job or not job.video_path:
        return JSONResponse({"error": "not ready"}, status_code=404)
    return FileResponse(job.video_path, media_type="video/mp4")


def _job_payload(job: pr.Job) -> dict:
    return {
        "id": job.id,
        "status": job.status,
        "message": job.message,
        "error": job.error,
        "video_url": f"/api/jobs/{job.id}/video" if job.video_path else None,
        "created_at": job.created_at,
    }


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


def main():
    import uvicorn
    import webbrowser
    import threading

    url = "http://127.0.0.1:8765"
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print(f"\nHero Studio running at {url}\n")
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")


if __name__ == "__main__":
    main()
