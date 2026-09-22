"""Remote license check ("kill switch") for distributed copies of Hero Studio.

How it works:
  - A secret GitHub Gist (readable by URL, writable only with an admin
    GitHub token) holds the license list: {"global_kill": bool, "licenses":
    {key: {"client": str, "status": "active"|"revoked", "machine_id": str|null}}}.
  - Every install fetches it on startup and periodically. If the install's
    configured key is missing/revoked, bound to a different machine, or
    global_kill is set, the app blocks itself with a clear message instead
    of running.
  - An install that holds RAD_ADMIN_TOKEN (a GitHub token with `gist`
    write scope) is the admin install: license checks don't apply to it, and
    it gets the Admin tab to activate/revoke keys and flip the kill switch.
    That token is set only in the maintainer's own .env - it is never part
    of what a client receives.
  - One-machine locking: clients never get write access to the license
    store (that's the whole point - only RAD_ADMIN_TOKEN can write). So
    binding a key to a specific device is a manual step: the client's app
    shows them a Machine ID in Settings, they send it to you once, and you
    paste it into the Admin tab when activating their key. From then on,
    check_license() rejects that key from any other machine. Leave
    machine_id blank on a license to allow it anywhere (e.g. for a trial).

Honesty check: this is a client-side check in a fully readable Python/JS app.
It stops the realistic case (a client keeps using it after they stop paying,
or hands the folder to someone else) because the app phones home and refuses
to run when revoked or device-mismatched. It will not stop someone willing to
read stage-by-stage through licensing.py and delete the call to
check_license(). Treat it as a deterrent and a usage signal, not unbreakable DRM.
"""
import hashlib
import time
import uuid as uuidlib

import requests

from . import config

CACHE_TTL_SECONDS = 6 * 3600

_cache: dict = {"data": None, "ts": 0}


def is_admin() -> bool:
    return bool(config.RAD_ADMIN_TOKEN)


_ID_FILE = config.ROOT / ".installation_id"


def get_machine_id() -> str:
    """A per-installation fingerprint, persisted on first run.

    Deliberately NOT derived from hardware (MAC address / uuid.getnode() is
    unreliable across environments - e.g. it returns a fresh random value
    every process start inside some sandboxes/VMs, which would silently
    break device locking). A random ID written to disk once and read back
    is boring but actually stable, which is the property that matters here.
    It's "one installed copy," not strictly "one physical machine" - deleting
    this file and relaunching gets a fresh ID, same as reinstalling would.
    Not spoof-proof; see the module docstring's honesty check.
    """
    if _ID_FILE.exists():
        return _ID_FILE.read_text().strip()

    digest = hashlib.sha256(uuidlib.uuid4().bytes).hexdigest()[:16].upper()
    machine_id = "-".join(digest[i:i + 4] for i in range(0, 16, 4))
    _ID_FILE.write_text(machine_id)
    return machine_id


def _fetch_remote() -> dict:
    resp = requests.get(config.LICENSE_GIST_URL, params={"_": int(time.time())}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_license_data(force_refresh: bool = False) -> dict:
    now = time.time()
    if force_refresh or _cache["data"] is None or now - _cache["ts"] > CACHE_TTL_SECONDS:
        _cache["data"] = _fetch_remote()
        _cache["ts"] = now
    return _cache["data"]


def check_license() -> dict:
    """Returns {"ok": bool, "reason": str}. Never raises."""
    if is_admin():
        return {"ok": True, "reason": "admin"}

    if not config.LICENSE_GIST_URL:
        return {"ok": True, "reason": "license backend not configured (open during development)"}

    try:
        data = get_license_data()
    except Exception:
        # Network/GitHub outage: fail open on a cached grace period rather
        # than bricking a legitimate user's app over a transient blip. If
        # there's no cache at all yet, this also fails open on first run.
        return {"ok": True, "reason": "license check unreachable, allowing (cached grace period)"}

    if data.get("global_kill"):
        return {"ok": False, "reason": "This app has been disabled by RAD Media Solutions. Contact them to restore access."}

    key = config.LICENSE_KEY
    if not key:
        return {"ok": False, "reason": "No license key configured. Add yours in Settings, or contact RAD Media Solutions."}

    lic = data.get("licenses", {}).get(key)
    if not lic or lic.get("status") != "active":
        return {"ok": False, "reason": "This license key is inactive. Contact RAD Media Solutions."}

    bound_machine = lic.get("machine_id")
    if bound_machine and bound_machine != get_machine_id():
        return {"ok": False, "reason": "This license is activated on a different device. Contact RAD Media Solutions to move it."}

    return {"ok": True, "reason": "licensed"}


# ---------- Admin-only write operations ----------

def _require_admin():
    if not is_admin():
        raise PermissionError("RAD_ADMIN_TOKEN not set - this install has no admin rights.")


def _write_remote(data: dict):
    import json

    gist_id = config.LICENSE_GIST_URL.rstrip("/").split("/")[-2] if "gist.githubusercontent.com" in config.LICENSE_GIST_URL else None
    if not gist_id:
        raise RuntimeError("Could not determine gist id from LICENSE_GIST_URL")

    resp = requests.patch(
        f"https://api.github.com/gists/{gist_id}",
        headers={
            "Authorization": f"token {config.RAD_ADMIN_TOKEN}",
            "Accept": "application/vnd.github+json",
        },
        json={"files": {"licenses.json": {"content": json.dumps(data, indent=2)}}},
        timeout=15,
    )
    resp.raise_for_status()
    _cache["data"] = data
    _cache["ts"] = time.time()


def add_license(key: str, client: str, machine_id: str = "") -> dict:
    _require_admin()
    data = get_license_data(force_refresh=True)
    data.setdefault("licenses", {})[key] = {
        "client": client,
        "status": "active",
        "machine_id": machine_id or None,
    }
    _write_remote(data)
    return data


def set_license_status(key: str, status: str) -> dict:
    _require_admin()
    data = get_license_data(force_refresh=True)
    if key not in data.get("licenses", {}):
        raise KeyError(f"No such license key: {key}")
    data["licenses"][key]["status"] = status
    _write_remote(data)
    return data


def set_license_machine(key: str, machine_id: str) -> dict:
    """Lock (or unlock, if machine_id is empty) an existing license to a device."""
    _require_admin()
    data = get_license_data(force_refresh=True)
    if key not in data.get("licenses", {}):
        raise KeyError(f"No such license key: {key}")
    data["licenses"][key]["machine_id"] = machine_id or None
    _write_remote(data)
    return data


def set_global_kill(enabled: bool) -> dict:
    _require_admin()
    data = get_license_data(force_refresh=True)
    data["global_kill"] = enabled
    _write_remote(data)
    return data
