#!/usr/bin/env python3
"""Check, or explicitly install, the optional pinned PPTAgent local runtime.

This script never installs OS packages, registers global skills, or calls models.
Run it inside Linux/WSL or macOS; native Windows is deliberately unsupported.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import venv
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from pptstudio import pptagent_bridge as bridge


def install() -> tuple[dict, int]:
    info = bridge.runtime_info()
    if not info["supported_platform"]:
        return {**info, "status": "unsupported_platform", "installed": False,
                "instruction": "Open this checkout in WSL/Linux or macOS and rerun --install. No WSL or system packages were installed."}, 2
    if "source_error" in info:
        return {**info, "status": "source_invalid", "installed": False}, 2
    checks = info.get("checks", {})
    missing = [name for name in ("node", "npm", "libreoffice") if not checks.get(name)]
    if sys.version_info < (3, 11):
        missing.append("python>=3.11")
    if missing:
        return {**info, "status": "missing_system_prerequisites", "installed": False,
                "missing": missing,
                "instruction": "Install these system prerequisites yourself, then rerun --install."}, 2
    root = Path(info["skill_path"]).parent
    marker = root / "runtime-status.json"
    marker.unlink(missing_ok=True)
    python = root / ".venv" / "bin" / "python"
    steps = []
    try:
        if not python.is_file():
            venv.EnvBuilder(with_pip=True).create(root / ".venv")
        commands = [
            ("python_dependencies", [str(python), "-m", "pip", "install", "-r", str(root / "requirements.txt")]),
            ("node_dependencies", ["npm", "ci", "--prefix", str(root)]),
            ("chromium", [str(python), "-m", "playwright", "install", "chromium"]),
        ]
        for name, command in commands:
            # Do not echo package-manager logs: configured package indexes may
            # contain credentials. The explicit --install authorizes downloads.
            completed = subprocess.run(command, cwd=root, capture_output=True,
                                       text=True, check=False, timeout=1800)
            steps.append({"step": name, "ok": completed.returncode == 0})
            if completed.returncode:
                return {"status": "install_failed", "installed": False, "steps": steps,
                        "failed_step": name,
                        "instruction": "Run the failed dependency command locally to inspect its full output; no credentials were printed."}, 1
        signature = bridge.vendor_signature()
        # doctor probes dependencies only. It never invokes a visual model.
        process = subprocess.run(
            [str(python), str(root / "scripts" / "pptagent.py"), "doctor", "--workspace", str(root)],
            cwd=root, capture_output=True, text=True, check=False, timeout=120)
        try:
            doctor = json.loads(process.stdout)
        except (json.JSONDecodeError, TypeError):
            doctor = {}
        passed = process.returncode == 0 and doctor.get("ok") is True
        # Persist boolean diagnostics only, never upstream config or stderr.
        status = {"ok": passed, "revision": bridge.REVISION, "vendor_signature": signature,
                  "checks": {str(key): value is True for key, value in doctor.get("checks", {}).items()}}
        marker.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        return {**bridge.runtime_info(), "status": "ready" if passed else "doctor_failed",
                "installed": True, "steps": steps, "doctor_checks": status["checks"],
                "instruction": "Read the pinned Skill and prepare an order handoff. Authoring and visual review still require the host AI."}, 0 if passed else 1
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "install_failed", "installed": False, "steps": steps,
                "error_type": type(exc).__name__,
                "instruction": "Check local prerequisites/network and rerun --install. No system packages or global Skills were installed."}, 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Read-only local discovery (default); no subprocess or downloads")
    mode.add_argument("--install", action="store_true", help="Explicitly create the local venv and download pip/npm/Chromium dependencies")
    args = parser.parse_args(argv)
    if args.install:
        payload, code = install()
    else:
        payload = {**bridge.runtime_info(), "status": "check_only", "installed": False}
        code = 0
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
