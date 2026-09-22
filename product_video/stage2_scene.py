"""Stage 2 — composite the isolated product into a premium scene.

Two interchangeable engines, both identity-preserving editors (they're given
the product cutout + an instruction, not asked to regenerate the product
from scratch — that's what keeps the label/shape from warping):

  local   FLUX.1 Kontext via mflux (Apple MLX). Free, no API key, no data
          leaves your machine. Apple Silicon only.
  openai  gpt-image-1-mini via your own OpenAI API key. Works on any
          platform (Windows/Linux/Mac). Cheapest OpenAI image model —
          "low" quality is ~$0.005-0.01/image. (Not Gemini/Nano Banana —
          deliberately not offered here, quality wasn't good enough.)
"""
import base64
import platform
import shutil
import subprocess
from pathlib import Path

from . import config

LOCAL_BINARY = "mflux-generate-kontext"


def local_engine_available() -> bool:
    is_apple_silicon = platform.system() == "Darwin" and platform.machine() == "arm64"
    return is_apple_silicon and shutil.which(LOCAL_BINARY) is not None


def compose_scene_local(
    product_png: str,
    scene_prompt: str,
    output_path: str,
    quantize: int = 4,
    steps: int = 20,
    seed: int | None = None,
) -> str:
    """FLUX.1 Kontext via mflux. Apple Silicon only.

    mflux's CLI flags shift between releases; if this fails, run
    `mflux-generate-kontext --help` and adjust the flags below.
    """
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError(
            "Local scene compositing needs Apple Silicon (mlx has no Windows/Linux "
            "wheels). Use the 'openai' engine instead."
        )
    if shutil.which(LOCAL_BINARY) is None:
        raise RuntimeError(
            f"{LOCAL_BINARY} not found on PATH. Install it with `pip install mflux` "
            "inside the project venv, then re-run."
        )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        LOCAL_BINARY,
        "--image-path", product_png,
        "--prompt", scene_prompt,
        "--output", output_path,
        "--steps", str(steps),
        "-q", str(quantize),
    ]
    if seed is not None:
        cmd += ["--seed", str(seed)]

    subprocess.run(cmd, check=True)
    return output_path


def compose_scene_openai(
    product_png: str,
    scene_prompt: str,
    output_path: str,
    model: str | None = None,
    quality: str = "low",
    size: str = "1024x1536",
) -> str:
    """gpt-image-1-mini (or your chosen model) edit endpoint, via your own key.

    The cutout's transparent background tells the model where it's free to
    paint the new scene; the opaque product pixels are preserved.
    """
    from openai import OpenAI

    if not config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set in .env / Settings")

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    model = model or config.OPENAI_IMAGE_MODEL

    with open(product_png, "rb") as f:
        result = client.images.edit(
            model=model,
            image=f,
            prompt=scene_prompt,
            quality=quality,
            size=size,
        )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_bytes(base64.b64decode(result.data[0].b64_json))
    return output_path


ENGINES = {"local": compose_scene_local, "openai": compose_scene_openai}


def compose_scene(engine: str, product_png: str, scene_prompt: str, output_path: str, **kwargs) -> str:
    if engine not in ENGINES:
        raise ValueError(f"Unknown scene engine '{engine}', pick one of {list(ENGINES)}")
    return ENGINES[engine](product_png, scene_prompt, output_path, **kwargs)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Composite a product cutout into a scene")
    parser.add_argument("product_png", help="Transparent product cutout from stage 1")
    parser.add_argument("prompt", help="Scene instruction, e.g. 'place on a marble pedestal under a glass dome in a sunlit flower field, studio lighting'")
    parser.add_argument("output", help="Path to write the hero image")
    parser.add_argument("--engine", choices=list(ENGINES), default="local" if local_engine_available() else "openai")
    parser.add_argument("-q", "--quantize", type=int, default=4, choices=[3, 4, 6, 8], help="local engine only")
    parser.add_argument("--steps", type=int, default=20, help="local engine only")
    parser.add_argument("--seed", type=int, default=None, help="local engine only")
    args = parser.parse_args()

    if args.engine == "local":
        out = compose_scene_local(args.product_png, args.prompt, args.output, args.quantize, args.steps, args.seed)
    else:
        out = compose_scene_openai(args.product_png, args.prompt, args.output)
    print(f"Wrote {out}")
