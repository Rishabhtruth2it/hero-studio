"""In-app update check/apply, driven by `git`.

Works when the install is a `git clone` (what "Code > Download ZIP" is not).
A ZIP install has no .git directory, so this reports update_available=False
with a note to re-download instead - there's no repo to pull from.
"""
import platform
import subprocess

from . import config

ROOT = config.ROOT


def _run(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)


def is_git_repo() -> bool:
    return (ROOT / ".git").exists()


def check_for_update() -> dict:
    if not is_git_repo():
        return {
            "git": False,
            "update_available": False,
            "message": "This copy wasn't installed via git, so it can't self-update. Download the latest ZIP from the repo instead.",
        }

    fetch = _run(["git", "fetch", "origin"])
    if fetch.returncode != 0:
        return {"git": True, "update_available": False, "error": fetch.stderr.strip() or "git fetch failed"}

    local = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    remote = _run(["git", "rev-parse", "origin/main"]).stdout.strip()
    if not local or not remote:
        return {"git": True, "update_available": False, "error": "couldn't resolve HEAD or origin/main"}

    log = _run(["git", "log", f"{local}..{remote}", "--oneline"]).stdout.strip()
    return {
        "git": True,
        "update_available": bool(log),
        "commits_behind": len(log.splitlines()) if log else 0,
        "local": local[:7],
        "remote": remote[:7],
    }


def _venv_python() -> str:
    if platform.system() == "Windows":
        return str(ROOT / ".venv" / "Scripts" / "python.exe")
    return str(ROOT / ".venv" / "bin" / "python")


def apply_update() -> dict:
    if not is_git_repo():
        return {"ok": False, "error": "Not a git checkout - re-download the latest ZIP from GitHub instead."}

    pull = _run(["git", "pull", "--ff-only", "origin", "main"], timeout=60)
    if pull.returncode != 0:
        return {"ok": False, "error": pull.stderr.strip() or pull.stdout.strip() or "git pull failed"}

    pip = _run([_venv_python(), "-m", "pip", "install", "-q", "-r", "requirements.txt"], timeout=300)

    return {
        "ok": True,
        "pull_output": pull.stdout.strip(),
        "dependencies_updated": pip.returncode == 0,
        "dependency_error": None if pip.returncode == 0 else pip.stderr.strip(),
    }
