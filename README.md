# Hero Studio

*by RAD Media Solutions*

Turn one product photo into a cinematic video — the same idea as Higgsfield,
Adobe Firefly, or Pixelcut's "photo to video" tools, but self-hosted and
running on **your own API keys**. No shared backend for the actual AI work,
no reseller markup: every install brings its own Runway/Kling/OpenAI key.

```
your photo
  -> [1] remove background        (rembg, local, free)
  -> [2] composite into a scene   (FLUX Kontext locally, or gpt-image-1-mini via your key — optional)
  -> [3] animate it                (Runway or Kling, your API key, paid per clip)
  -> [4] burn in captions          (ffmpeg, local, free)
```

An in-app wizard can also write the scene/motion prompts for you from four
plain-language questions, using GPT (needs an OpenAI key).

## Install

**One link, works for anyone, no GitHub account needed:**
[github.com/Rishabhtruth2it/hero-studio/archive/refs/heads/main.zip](https://github.com/Rishabhtruth2it/hero-studio/archive/refs/heads/main.zip)

That link downloads the whole app as a ZIP immediately. Unzip it, then:

**Mac** — double-click **`Launch Hero Studio.command`**.

**Windows** — double-click **`Launch Hero Studio.bat`**.

(If you'd rather clone with `git` so you get update notifications later,
that also works — the repo is public: `git clone
https://github.com/Rishabhtruth2it/hero-studio.git`.)

Either way, first run installs everything automatically (a local Python
3.11, a virtual environment, all dependencies) — no admin password needed.
Every run after that opens in seconds. Your browser opens to
`http://127.0.0.1:8765`.

On first open, go to **Settings** and add your own key(s):

- **Runway** — [dev.runwayml.com](https://dev.runwayml.com) → Organization → API Keys. Needs a balance top-up (min $10).
- **Kling** — [kling.ai/dev/api-key](https://kling.ai/dev/api-key). Needs a resource package purchased first.
- **OpenAI** (optional, only for scene compositing on Windows or if you skip the free local Mac engine) — [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
- **License key** — whatever RAD Media Solutions gave you when you signed up.

Every key is written to a local `.env` file on your machine only — never
sent anywhere except the official provider it belongs to.

Mac may warn the launcher is from an unidentified developer the first time:
right-click it → **Open** → **Open** to approve it once. Windows may show a
SmartScreen warning for the same reason: **More info** → **Run anyway**.

### Platform notes

- **Local scene compositing (FLUX Kontext) is Apple Silicon only.** On
  Windows/Intel Mac/Linux, use the OpenAI engine instead (~$0.01/image,
  works everywhere) — the app picks this automatically when local isn't
  available.
- Everything else (background removal, the video API calls, captions) works
  identically on every platform.

### Desktop app (admin machine only)

`desktop/build-app.sh` builds a real `Hero Studio.app` (with the RAD logo as
its icon) and installs it to `/Applications` — launchable from Spotlight,
Launchpad, or the Dock like any native app, no terminal needed after the
first build. It's meant for the maintainer's own machine (where
`RAD_ADMIN_TOKEN` already lives), not something to hand to clients — they
use `Launch Hero Studio.command`/`.bat` instead. Re-run the script any time
to refresh the installed app in place:

```bash
bash desktop/build-app.sh
```

## Using the app

**Create**: drop in a product photo, either answer the ✨ four-question
wizard to have GPT write your prompts, or write your own. Pick a provider,
hit **Generate**. Result streams in with a progress tracker.
**History**: past generations from this session.
**Settings**: your API keys and license key.

## Licensing (RAD Media Solutions internal)

Every install phones home to a license check on startup. This is honest
about what it is: a **deterrent**, not unbreakable DRM — the app is fully
readable Python/JS, so a determined developer could eventually strip the
check out. What it reliably stops is the realistic case: a client (or
whoever they hand the folder to) keeps using it after they've stopped
paying.

- **One key per client**, generated manually in the **Admin** tab (only
  visible on the maintainer's own install — see below).
- **One machine per key, by default**: the app shows the client a Machine ID
  in Settings; they send it to you once; you paste it in when activating
  their license in Admin. From then on that key only works on that device.
  Uncheck **"Lock this license to one device"** when adding a license (or
  hit **Allow any device** on an existing one) to skip this entirely for
  people you trust on multiple machines.
- **Kill switch**: revoke a single client's key, or flip the global kill
  switch to block every non-admin install at once.

The Admin tab only appears on an install that has `RAD_ADMIN_TOKEN` set in
its own `.env` (a GitHub token with `gist` scope) — that variable must
**never** go into a client's `.env`. See `.env.example` for setup.

The license store itself is a secret GitHub Gist (`LICENSE_GIST_URL` in
`.env`) — already created for the current admin install. Setting up a
*different* machine as an additional admin means copying both
`RAD_ADMIN_TOKEN` and `LICENSE_GIST_URL` into that machine's `.env`.

## Updates

If a client installed via `git clone` (not the ZIP), the app checks GitHub
for new commits on startup and shows an **Update available** banner they
can click — it runs `git pull` + reinstalls any new dependencies, then asks
them to restart the app. ZIP installs don't get this (no `.git` to pull
from) — re-download the ZIP instead.

To ship an update: commit and push to `main` as usual. Every git-cloned
install picks it up automatically.

## Security

The server only binds to `127.0.0.1` (never reachable over the network),
and a same-origin check rejects any cross-site request to every
state-changing endpoint — confirmed by actually attacking a live instance
during development, not just reasoned about: an early version let a plain
cross-origin `<form>` POST silently trigger `/api/update/apply` (a real
`git pull` + dependency reinstall) with zero friction from any website the
admin happened to have open. Also in place: upload validation (image
content-type + 25MB cap) on the photo-upload endpoint, output-escaping on
every value rendered into the page (client names, keys, job messages) to
close a stored-XSS path in the Admin table, `X-Frame-Options`/CSP headers
against clickjacking, and `.env` staying at `600` permissions (owner-only)
through every rewrite.

What's *not* fixed, because it can't be from inside the app, and is worth
knowing rather than assuming away:

- **The license check is a deterrent, not DRM.** The app is fully readable
  Python/JS; anyone willing to read `product_video/licensing.py` can delete
  the call to `check_license()`. It stops casual non-payment, not a
  determined developer.
- **The license check fails open on a network error**, by design — an
  unreachable Gist (GitHub outage, blocked DNS) lets the app keep running
  on its last-cached result rather than bricking a legitimate user over a
  transient blip. That also means someone could block the app's access to
  `api.github.com`/`gist.githubusercontent.com` to force permanent
  fail-open — a real bypass, and a deliberate tradeoff against the
  alternative (annoying legitimate users far more often than it stops
  anyone determined).
- **The Machine ID isn't hardware-attested** — it's a random value written
  to `.installation_id` on first run, not derived from real hardware (MAC-
  address-based fingerprinting proved unreliable across environments during
  testing — see the comment in `licensing.py`). Deleting that file and
  relaunching gets a fresh ID.

## Command-line usage (advanced)

The same pipeline is available as a CLI:

```bash
source .venv/bin/activate   # .venv\Scripts\activate on Windows
python -m product_video.cli input/perfume.jpg \
  --scene-prompt "place the bottle on a white marble pedestal inside a glass \
                   dome, surrounded by soft-focus pink and cream flowers, \
                   warm golden hour light, shallow depth of field" \
  --motion-prompt "the glass dome slowly lifts and floats upward as flower \
                    petals drift through the air, camera pushes in slowly" \
  --provider runway \
  --caption "COCO. The one everyone asks about."
```

Output lands in `output/<photo-name>/4_final.mp4`. Each stage also runs
standalone:

```bash
python -m product_video.stage1_cleanup input/perfume.jpg cutout.png
python -m product_video.stage2_scene cutout.png "on a marble pedestal, studio light" hero.png --engine openai
python -m product_video.stage3_animate hero.png "camera slowly orbits the product" out.mp4 --provider kling
python -m product_video.stage4_assemble out.mp4 "Your caption here" final.mp4
```

## Known limits / things to check before relying on this

- **mflux CLI flags drift between releases.** If local scene compositing
  errors, run `mflux-generate-kontext --help` and adjust
  `product_video/stage2_scene.py` — see the [mflux repo](https://github.com/mflux-community/mflux).
- **16GB RAM is tight for the local FLUX model.** Defaults to 4-bit
  quantization; drop to `-q 3` if it's swapping heavily, or just use the
  OpenAI engine instead.
- **Kling's exact endpoint/model names change as they ship new versions.**
  Check [kling.ai/document-api](https://kling.ai/document-api) if you get a
  404, and update `KLING_MODEL` / `KLING_API_BASE`.
- **OpenAI model retirements move fast.** `gpt-image-1` itself is being
  retired Oct 2026; this defaults to `gpt-image-1-mini`. Check
  [platform.openai.com/docs/models](https://platform.openai.com/docs/models)
  if image generation starts failing.
- **No automated defect/watermark cleanup.** That's inherently manual. Run
  `iopaint start --model=lama --device=cpu` separately (`pip install
  iopaint`) if you need it.
- **This repo is public** so the install link works for anyone with no
  GitHub account. That means the source (including how the license check
  works) is publicly readable — nothing sensitive lives in it, though:
  license keys, the admin token, and every user's API keys only ever exist
  in local `.env` files, never in git.
- **Licensing is a deterrent, not DRM** — see the Licensing section above.
