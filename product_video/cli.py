"""End-to-end pipeline: one product photo -> finished cinematic vertical video.

Example:
    python -m product_video.cli input/perfume.jpg \\
        --scene-prompt "place on a white marble pedestal inside a glass dome, \\
                         surrounded by soft-focus pink flowers, golden hour light" \\
        --motion-prompt "the glass dome slowly lifts as flower petals drift \\
                          through the air, camera pushes in slowly" \\
        --provider runway \\
        --caption "COCO. The one everyone asks about."

Any stage can be skipped with --start-from / --skip-* if you already have
intermediate files (e.g. you hand-edited the hero image before animating it).
"""
import argparse
from pathlib import Path

from . import config
from .stage1_cleanup import remove_background
from .stage2_scene import compose_scene, local_engine_available
from .stage3_animate import animate
from .stage4_assemble import add_caption


def run(args: argparse.Namespace) -> str:
    stem = Path(args.input).stem
    work = config.OUTPUT_DIR / stem
    work.mkdir(parents=True, exist_ok=True)

    cutout_path = work / "1_cutout.png"
    hero_path = work / "2_hero.png"
    video_path = work / f"3_video_{args.provider}.mp4"
    final_path = work / "4_final.mp4"

    if not args.skip_cleanup:
        print("[1/4] Removing background...")
        remove_background(args.input, str(cutout_path))
    else:
        cutout_path = Path(args.input)

    if not args.skip_scene:
        print(f"[2/4] Compositing scene ({args.scene_engine})...")
        kwargs = {"quantize": args.quantize} if args.scene_engine == "local" else {}
        compose_scene(args.scene_engine, str(cutout_path), args.scene_prompt, str(hero_path), **kwargs)
    else:
        hero_path = cutout_path

    print(f"[3/4] Animating via {args.provider}...")
    animate(args.provider, str(hero_path), args.motion_prompt, str(video_path))

    result_path = video_path
    if args.caption:
        print("[4/4] Adding caption...")
        add_caption(str(video_path), args.caption, str(final_path))
        result_path = final_path
    else:
        print("[4/4] No caption requested, skipping.")

    print(f"\nDone: {result_path}")
    return str(result_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", help="Source product photo")
    parser.add_argument("--scene-prompt", required=True, help="How to place the product in a scene (stage 2)")
    parser.add_argument("--motion-prompt", required=True, help="How the camera/scene should move (stage 3)")
    parser.add_argument("--provider", choices=["runway", "kling"], default="runway")
    parser.add_argument("--caption", default=None, help="Burned-in caption text")
    parser.add_argument(
        "--scene-engine",
        choices=["local", "openai"],
        default="local" if local_engine_available() else "openai",
        help="local = free FLUX via mflux (Apple Silicon only); openai = gpt-image-1-mini, your own key, any platform",
    )
    parser.add_argument("--quantize", type=int, default=4, choices=[3, 4, 6, 8], help="local engine only: FLUX quantization (lower = less RAM)")
    parser.add_argument("--skip-cleanup", action="store_true", help="Input is already background-removed")
    parser.add_argument("--skip-scene", action="store_true", help="Input is already the final hero image")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
