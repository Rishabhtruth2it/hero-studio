# Hero Studio

Turn one product photo into a cinematic video — the same idea as Higgsfield,
Adobe Firefly, or Pixelcut's "photo to video" tools, but self-hosted and
running on **your own API keys**. There's no shared backend, no reseller
markup, and no account with us: everything runs on your machine, and every
person who installs it brings their own Runway/Kling key.

```
your photo
  -> [1] remove background        (rembg, local, free)
  -> [2] composite into a scene   (FLUX.1 Kontext via mflux, local, free, optional)
  -> [3] animate it                (Runway or Kling, your API key, paid per clip)
  -> [4] burn in captions          (ffmpeg, local, free)
```

## Install

**Requires a Mac** (Apple Silicon or Intel; local scene compositing needs
Apple Silicon specifically, but the rest works on any Mac).

1. Download this repository: **Code → Download ZIP** (top of this page), then unzip it. Or, if you have `git`:
   ```bash
   git clone https://github.com/<owner>/<repo>.git
   ```
2. Double-click **`Launch Hero Studio.command`**.
   - First run installs everything automatically (a local Python 3.11, a virtual environment, and all dependencies) — no Homebrew, no admin password, takes a few minutes.
   - Every run after that opens instantly.
3. Your browser opens to `http://127.0.0.1:8765`. Go to **Settings** and paste in your own API key:
   - **Runway** — [dev.runwayml.com](https://dev.runwayml.com) → Organization → API Keys. Needs a small balance top-up (min $10) before it'll generate.
   - **Kling** — [kling.ai/dev/api-key](https://kling.ai/dev/api-key). Needs a resource package purchased first.

Your key is written to a local `.env` file on your machine only. It is never sent anywhere except the provider it belongs to (Runway's API only sees the Runway key, etc.) — not to us, not to each other.

macOS may warn that the script is from an unidentified developer the first time. Right-click the file → **Open** → **Open** to approve it once.

## Using the app

Open the **Create** tab: drop in a product photo, pick or write a motion
prompt, choose a provider, hit **Generate**. The result streams in with a
progress tracker and is downloadable when done. Past generations live under
**History**.

## Command-line usage (advanced)

The same pipeline is available as a CLI if you'd rather script it or run it headless:

```bash
source .venv/bin/activate
python -m product_video.cli input/perfume.jpg \
  --scene-prompt "place the bottle on a white marble pedestal inside a glass \
                   dome, surrounded by soft-focus pink and cream flowers, \
                   warm golden hour light, shallow depth of field" \
  --motion-prompt "the glass dome slowly lifts and floats upward as flower \
                    petals drift through the air, camera pushes in slowly" \
  --provider runway \
  --caption "COCO. The one everyone asks about."
```

Output lands in `output/<photo-name>/4_final.mp4`, with every intermediate
file kept alongside it. Each stage is also runnable standalone:

```bash
python -m product_video.stage1_cleanup input/perfume.jpg cutout.png
python -m product_video.stage2_scene cutout.png "on a marble pedestal, studio light" hero.png
python -m product_video.stage3_animate hero.png "camera slowly orbits the product" out.mp4 --provider kling
python -m product_video.stage4_assemble out.mp4 "Your caption here" final.mp4
```

### Cheap draft, expensive final

Generate on Runway first (~$0.25 for a 5s clip) to dial in your motion
prompt, then re-run just stage 3 on Kling (~$0.50/clip) for the shot you're
actually publishing:

```bash
python -m product_video.stage3_animate output/perfume/2_hero.png \
  "the glass dome slowly lifts as petals drift" \
  output/perfume/3_video_kling.mp4 --provider kling
```

## Known limits / things to check before relying on this

- **mflux CLI flags drift between releases.** If scene compositing errors,
  run `mflux-generate-kontext --help` and adjust `product_video/stage2_scene.py`
  — the model list and CLI surface change often (see the
  [mflux repo](https://github.com/mflux-community/mflux) for current docs).
- **16GB RAM is tight for a 12GB model.** Scene compositing defaults to
  4-bit quantization to fit; it's slow (a few minutes per image) and a step
  below full-precision quality. Drop to `-q 3` if it's swapping heavily.
- **Kling's exact endpoint/model names change as they ship new versions.**
  Check [kling.ai/document-api](https://kling.ai/document-api) if you get a
  404 or "model not found," and update `KLING_MODEL` / `KLING_API_BASE` in Settings/`.env`.
- **No automated defect/watermark cleanup.** That's inherently a manual,
  draw-a-mask task. Run `iopaint start --model=lama --device=cpu` separately
  (`pip install iopaint`) and use its web UI if you need it.
- **This repo is private.** Anyone you want to use it needs to be added as a
  collaborator (or the repo made public) before they can clone or download it.
