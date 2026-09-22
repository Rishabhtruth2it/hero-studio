"""Background job runner wrapping the product_video pipeline stages for the web UI."""
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from product_video import config
from product_video.stage1_cleanup import remove_background
from product_video.stage2_scene import compose_scene
from product_video.stage3_animate import animate
from product_video.stage4_assemble import add_caption

STAGE_LABELS = {
    "queued": "Queued",
    "removing_bg": "Removing background",
    "enhancing_scene": "Compositing scene (local AI, this can take a few minutes)",
    "animating": "Generating motion",
    "captioning": "Adding caption",
    "done": "Done",
    "error": "Failed",
}


@dataclass
class Job:
    id: str
    status: str = "queued"
    message: str = STAGE_LABELS["queued"]
    error: Optional[str] = None
    video_path: Optional[str] = None
    thumb_path: Optional[str] = None
    created_at: float = field(default_factory=time.time)


JOBS: dict[str, Job] = {}
_lock = threading.Lock()


def new_job_id() -> str:
    return uuid.uuid4().hex[:10]


def create_job(
    job_id: str,
    input_path: str,
    motion_prompt: str,
    provider: str,
    caption: Optional[str] = None,
    enhance_scene: bool = False,
    scene_prompt: Optional[str] = None,
    scene_engine: str = "local",
    quantize: int = 4,
) -> Job:
    job = Job(id=job_id, thumb_path=input_path)
    with _lock:
        JOBS[job_id] = job

    thread = threading.Thread(
        target=_run_job,
        args=(job, input_path, motion_prompt, provider, caption, enhance_scene, scene_prompt, scene_engine, quantize),
        daemon=True,
    )
    thread.start()
    return job


def _set(job: Job, status: str, message: str | None = None):
    job.status = status
    job.message = message or STAGE_LABELS.get(status, status)


def _run_job(
    job: Job,
    input_path: str,
    motion_prompt: str,
    provider: str,
    caption: Optional[str],
    enhance_scene: bool,
    scene_prompt: Optional[str],
    scene_engine: str,
    quantize: int,
):
    work = config.OUTPUT_DIR / job.id
    work.mkdir(parents=True, exist_ok=True)

    try:
        hero_path = input_path

        if enhance_scene:
            _set(job, "removing_bg")
            cutout_path = work / "1_cutout.png"
            remove_background(input_path, str(cutout_path))

            _set(job, "enhancing_scene", f"Compositing scene via {scene_engine}...")
            scene_out = work / "2_hero.png"
            scene_kwargs = {"quantize": quantize} if scene_engine == "local" else {}
            compose_scene(scene_engine, str(cutout_path), scene_prompt or motion_prompt, str(scene_out), **scene_kwargs)
            hero_path = str(scene_out)

        _set(job, "animating", f"Generating motion via {provider}...")
        video_path = work / f"3_video_{provider}.mp4"
        animate(provider, hero_path, motion_prompt, str(video_path))

        result_path = video_path
        if caption:
            _set(job, "captioning")
            final_path = work / "4_final.mp4"
            add_caption(str(video_path), caption, str(final_path))
            result_path = final_path

        job.video_path = str(result_path)
        _set(job, "done")
    except Exception as e:  # noqa: BLE001 - surface any failure to the UI
        job.error = str(e)
        _set(job, "error", str(e))
