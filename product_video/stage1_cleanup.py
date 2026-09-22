"""Stage 1 — isolate the product from its source photo. Fully local, free, no API key.

Uses rembg's bria-rmbg model (best local quality for hard-edged subjects like
products). Output is a transparent PNG ready to be dropped into any scene.
"""
from pathlib import Path
from rembg import remove, new_session

_session = None


def remove_background(input_path: str, output_path: str, model: str = "bria-rmbg") -> str:
    global _session
    if _session is None or _session.model_name != model:
        _session = new_session(model)

    data = Path(input_path).read_bytes()
    cutout = remove(data, session=_session, decontaminate=True)
    Path(output_path).write_bytes(cutout)
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Remove background from a product photo")
    parser.add_argument("input", help="Path to source product photo")
    parser.add_argument("output", help="Path to write transparent PNG")
    parser.add_argument("--model", default="bria-rmbg")
    args = parser.parse_args()

    out = remove_background(args.input, args.output, args.model)
    print(f"Wrote {out}")
