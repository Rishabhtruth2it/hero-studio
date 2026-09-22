"""Stage 3 — animate the hero image into a cinematic clip.

This is the one stage that calls out to a paid, official, first-party API —
there's no local model on a 16GB Mac that matches this quality/speed. You
bring your own key; nothing routes through a third-party reseller.

Providers:
  runway  -> Runway Dev API (gen4_turbo / gen4.5), https://dev.runwayml.com
  kling   -> Kling AI Open Platform, https://kling.ai/dev

Both take the same three inputs (image, motion prompt, duration) so you can
generate a cheap Runway draft to dial in the prompt, then re-run the same
call on Kling for the final shot.
"""
import base64
import mimetypes
import time
from pathlib import Path

import requests

from . import config


def _image_to_data_uri(image_path: str) -> str:
    mime = mimetypes.guess_type(image_path)[0] or "image/png"
    data = Path(image_path).read_bytes()
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def _download(url: str, output_path: str) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)
    return output_path


def animate_runway(
    image_path: str,
    motion_prompt: str,
    output_path: str,
    model: str = "gen4_turbo",
    ratio: str = "720:1280",
    duration: int = 5,
) -> str:
    from runwayml import RunwayML, TaskFailedError

    if not config.RUNWAYML_API_SECRET:
        raise RuntimeError("RUNWAYML_API_SECRET is not set in .env")

    client = RunwayML(api_key=config.RUNWAYML_API_SECRET)

    try:
        task = client.image_to_video.create(
            model=model,
            prompt_image=_image_to_data_uri(image_path),
            prompt_text=motion_prompt,
            ratio=ratio,
            duration=duration,
        ).wait_for_task_output()
    except TaskFailedError as e:
        raise RuntimeError(f"Runway generation failed: {e.task_details}") from e

    video_url = task.output[0]
    return _download(video_url, output_path)


def animate_kling(
    image_path: str,
    motion_prompt: str,
    output_path: str,
    duration: str = "5",
    poll_interval: float = 5.0,
    timeout: float = 600.0,
) -> str:
    if not config.KLING_API_KEY:
        raise RuntimeError("KLING_API_KEY is not set in .env")

    headers = {
        "Authorization": f"Bearer {config.KLING_API_KEY}",
        "Content-Type": "application/json",
    }
    base = config.KLING_API_BASE.rstrip("/")

    submit = requests.post(
        f"{base}/v1/videos/image2video",
        headers=headers,
        json={
            "model_name": config.KLING_MODEL,
            "image": _image_to_data_uri(image_path),
            "prompt": motion_prompt,
            "duration": duration,
        },
        timeout=60,
    )
    submit.raise_for_status()
    task_id = submit.json()["data"]["task_id"]

    deadline = time.time() + timeout
    while time.time() < deadline:
        poll = requests.get(
            f"{base}/v1/videos/image2video/{task_id}",
            headers=headers,
            timeout=30,
        )
        poll.raise_for_status()
        data = poll.json()["data"]
        status = data.get("task_status")

        if status == "succeed":
            video_url = data["task_result"]["videos"][0]["url"]
            return _download(video_url, output_path)
        if status == "failed":
            raise RuntimeError(f"Kling generation failed: {data.get('task_status_msg')}")

        time.sleep(poll_interval)

    raise TimeoutError(f"Kling task {task_id} did not finish within {timeout}s")


PROVIDERS = {"runway": animate_runway, "kling": animate_kling}


def animate(provider: str, image_path: str, motion_prompt: str, output_path: str, **kwargs) -> str:
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider '{provider}', pick one of {list(PROVIDERS)}")
    return PROVIDERS[provider](image_path, motion_prompt, output_path, **kwargs)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Animate a hero image into a cinematic clip")
    parser.add_argument("image", help="Hero image from stage 2")
    parser.add_argument("prompt", help="Motion description, e.g. 'the glass dome slowly lifts as petals drift in the breeze'")
    parser.add_argument("output", help="Path to write the mp4")
    parser.add_argument("--provider", choices=list(PROVIDERS), default="runway")
    args = parser.parse_args()

    out = animate(args.provider, args.image, args.prompt, args.output)
    print(f"Wrote {out}")
