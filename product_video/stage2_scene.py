"""Stage 2 — composite the isolated product into a premium scene.

Runs FLUX.1 Kontext locally via mflux (Apple MLX). Free, no API key, no data
leaves your machine. Kontext is an *editing* model — it's given the cutout
and an instruction, and preserves the product's identity while changing the
scene around it (this is what keeps the label/shape from warping, unlike a
plain text-to-image regeneration).

16GB Macs: use -q 4 (4-bit quantization) or the pipeline will likely swap /
crash. It's slower but fits in memory. First run downloads the FLUX.1 Kontext
weights (~12GB) — that only happens once.

mflux's CLI flags shift between releases; if this fails, run
`mflux-generate-kontext --help` and adjust QUANT/STEPS/EXTRA_ARGS below.
"""
import shutil
import subprocess
from pathlib import Path

BINARY = "mflux-generate-kontext"


def compose_scene(
    product_png: str,
    scene_prompt: str,
    output_path: str,
    quantize: int = 4,
    steps: int = 20,
    seed: int | None = None,
) -> str:
    if shutil.which(BINARY) is None:
        raise RuntimeError(
            f"{BINARY} not found on PATH. Install it with `pip install mflux` "
            "inside the project venv, then re-run."
        )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        BINARY,
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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Composite a product cutout into a scene with FLUX Kontext")
    parser.add_argument("product_png", help="Transparent product cutout from stage 1")
    parser.add_argument("prompt", help="Scene instruction, e.g. 'place on a marble pedestal under a glass dome in a sunlit flower field, studio lighting'")
    parser.add_argument("output", help="Path to write the hero image")
    parser.add_argument("-q", "--quantize", type=int, default=4, choices=[3, 4, 6, 8])
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    out = compose_scene(args.product_png, args.prompt, args.output, args.quantize, args.steps, args.seed)
    print(f"Wrote {out}")
