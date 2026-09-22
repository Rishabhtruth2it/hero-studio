"""Hero Studio — local web app for the product_video pipeline.

Runs entirely on the user's machine. API keys are written to a local .env
file next to this project and never sent anywhere except the official
provider (Runway / Kling) they belong to.
"""
import platform
from pathlib import Path

from dotenv import dotenv_values, set_key
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from product_video import config, licensing, updater
from product_video.stage2_scene import local_engine_available
from product_video.prompt_helper import generate_prompts
from . import pipeline_runner as pr

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
STATIC_DIR = Path(__file__).resolve().parent / "static"
UPLOAD_DIR = config.OUTPUT_DIR / "_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

PORT = 8765
ALLOWED_ORIGINS = {f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"}

app = FastAPI(title="Hero Studio")


@app.middleware("http")
async def same_origin_guard(request: Request, call_next):
    """Block cross-site requests to every state-changing endpoint.

    This is a local server with no login system, so nothing else stops a
    malicious website from silently POSTing to it from a background tab -
    confirmed live: an unguarded /api/update/apply let a plain cross-origin
    POST trigger a real `git pull` + dependency reinstall with zero
    friction. Browsers attach `Origin` on every cross-site POST/PUT/PATCH/
    DELETE, so rejecting any request whose Origin doesn't match our own
    closes that off without affecting same-origin use of the app itself
    (same-origin requests either omit Origin or send ours).
    """
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        origin = request.headers.get("origin")
        if origin and origin not in ALLOWED_ORIGINS:
            return JSONResponse({"error": "Cross-site requests are not allowed."}, status_code=403)

    response = await call_next(request)

    # Clickjacking: without this, a malicious page could iframe the app and
    # trick the admin into clicking through an invisible overlay onto e.g.
    # the kill switch. No legitimate use of this app embeds it in a frame.
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/health")
def health():
    return {"ok": True}


def _mask(value: str | None) -> str | None:
    return f"•••• {value[-4:]}" if value else None


@app.get("/api/platform")
def get_platform():
    return {
        "os": platform.system(),
        "local_scene_engine_available": local_engine_available(),
    }


@app.get("/api/license/status")
def license_status():
    result = licensing.check_license()
    result["is_admin"] = licensing.is_admin()
    result["machine_id"] = licensing.get_machine_id()
    return result


@app.get("/api/update/check")
def update_check():
    return updater.check_for_update()


@app.post("/api/update/apply")
def update_apply():
    return updater.apply_update()


def _require_admin():
    if not licensing.is_admin():
        return JSONResponse({"error": "Admin access required."}, status_code=403)
    return None


@app.get("/api/admin/licenses")
def admin_list_licenses():
    denied = _require_admin()
    if denied:
        return denied
    try:
        return licensing.get_license_data(force_refresh=True)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/admin/licenses")
async def admin_mutate_license(payload: dict):
    denied = _require_admin()
    if denied:
        return denied
    action = payload.get("action")
    try:
        if action == "add":
            data = licensing.add_license(payload["key"], payload.get("client", ""), payload.get("machine_id", ""))
        elif action == "revoke":
            data = licensing.set_license_status(payload["key"], "revoked")
        elif action == "activate":
            data = licensing.set_license_status(payload["key"], "active")
        elif action == "bind_machine":
            data = licensing.set_license_machine(payload["key"], payload.get("machine_id", ""))
        elif action == "global_kill":
            data = licensing.set_global_kill(bool(payload.get("enabled")))
        else:
            return JSONResponse({"error": f"Unknown action '{action}'"}, status_code=400)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=500)
    return data


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
        "openai": {
            "configured": bool(vals.get("OPENAI_API_KEY")),
            "masked": _mask(vals.get("OPENAI_API_KEY")),
            "model": vals.get("OPENAI_IMAGE_MODEL", "gpt-image-1-mini"),
        },
        "license": {
            "configured": bool(vals.get("HERO_STUDIO_LICENSE_KEY")),
            "masked": _mask(vals.get("HERO_STUDIO_LICENSE_KEY")),
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

    if payload.get("openai_key"):
        set_key(str(ENV_PATH), "OPENAI_API_KEY", payload["openai_key"])
        config.OPENAI_API_KEY = payload["openai_key"]

    if payload.get("openai_model"):
        set_key(str(ENV_PATH), "OPENAI_IMAGE_MODEL", payload["openai_model"])
        config.OPENAI_IMAGE_MODEL = payload["openai_model"]

    if payload.get("license_key"):
        set_key(str(ENV_PATH), "HERO_STUDIO_LICENSE_KEY", payload["license_key"])
        config.LICENSE_KEY = payload["license_key"]

    return {"ok": True}


@app.post("/api/prompt-helper")
async def prompt_helper(payload: dict):
    if not config.OPENAI_API_KEY:
        return JSONResponse({"error": "No OpenAI API key configured. Add one in Settings first."}, status_code=400)
    try:
        result = generate_prompts(
            product=payload.get("product", ""),
            vibe=payload.get("vibe", ""),
            setting=payload.get("setting", ""),
            action=payload.get("action", ""),
            notes=payload.get("notes", ""),
        )
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=500)
    return result


MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_UPLOAD_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


@app.post("/api/jobs")
async def create_job(
    file: UploadFile = File(...),
    motion_prompt: str = Form(...),
    provider: str = Form("runway"),
    caption: str = Form(""),
    enhance_scene: bool = Form(False),
    scene_prompt: str = Form(""),
    scene_engine: str = Form("local"),
    quantize: int = Form(4),
):
    lic = licensing.check_license()
    if not lic["ok"]:
        return JSONResponse({"error": lic["reason"]}, status_code=403)

    if not (file.content_type or "").startswith("image/"):
        return JSONResponse({"error": "Only image uploads are allowed."}, status_code=400)

    job_id = pr.new_job_id()
    suffix = Path(file.filename or "upload.jpg").suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        suffix = ".jpg"
    dest = UPLOAD_DIR / f"{job_id}{suffix}"

    written = 0
    with open(dest, "wb") as f:
        while chunk := await file.read(1 << 20):
            written += len(chunk)
            if written > MAX_UPLOAD_BYTES:
                f.close()
                dest.unlink(missing_ok=True)
                return JSONResponse({"error": "Image is too large (25MB max)."}, status_code=413)
            f.write(chunk)

    if provider == "runway" and not config.RUNWAYML_API_SECRET:
        return JSONResponse({"error": "No Runway API key configured. Add one in Settings first."}, status_code=400)
    if provider == "kling" and not config.KLING_API_KEY:
        return JSONResponse({"error": "No Kling API key configured. Add one in Settings first."}, status_code=400)
    if enhance_scene and scene_engine == "openai" and not config.OPENAI_API_KEY:
        return JSONResponse({"error": "No OpenAI API key configured. Add one in Settings first."}, status_code=400)
    if enhance_scene and scene_engine == "local" and not local_engine_available():
        return JSONResponse({"error": "Local scene compositing needs Apple Silicon. Pick the OpenAI engine instead."}, status_code=400)

    pr.create_job(
        job_id,
        str(dest),
        motion_prompt,
        provider,
        caption or None,
        enhance_scene,
        scene_prompt or None,
        scene_engine,
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

    url = f"http://127.0.0.1:{PORT}"
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print(f"\nHero Studio running at {url}\n")
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
