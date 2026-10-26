"""Opt-in project-local skill install. Never edits a global AI configuration."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Copy this repository's workflow skill into .agents/skills.")
    parser.add_argument("--force", action="store_true", help="Explicitly replace an existing project-local skill")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    source = root / "skills" / "ppt-order-workflow"
    target = root / ".agents" / "skills" / "ppt-order-workflow"
    if not target.resolve().is_relative_to(root):
        parser.error("Skill destination resolves outside this repository")
    if target.exists() and not args.force:
        parser.error("Project skill already exists; inspect it first or pass --force")
    shutil.copytree(source, target, dirs_exist_ok=args.force)
    print(f"Installed project-local skill: {target}")
    print("For hosts without project skill discovery, read AI_START_HERE.md manually.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
