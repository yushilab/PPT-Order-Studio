"""Opt-in project-local skill install. Never edits a global AI configuration."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install project-owned workflow/design Skills into .agents/skills.")
    parser.add_argument("--skill", choices=["workflow", "design", "all"], default="all")
    parser.add_argument("--force", action="store_true", help="Explicitly replace an existing project-local skill")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    names = {"workflow": "ppt-order-workflow", "design": "ppt-order-design"}
    selected = list(names.values()) if args.skill == "all" else [names[args.skill]]
    pairs = []
    for name in selected:
        source = root / "skills" / name
        target = root / ".agents" / "skills" / name
        if not source.is_dir():
            parser.error(f"Skill source is missing: {source}")
        if not target.resolve().is_relative_to(root):
            parser.error("Skill destination resolves outside this repository")
        if target.exists() and not args.force:
            parser.error(f"Project skill already exists: {name}; inspect it first or pass --force")
        pairs.append((source, target))
    for source, target in pairs:
        shutil.copytree(source, target, dirs_exist_ok=args.force)
        print(f"Installed project-local skill: {target}")
    print("PPTAgent remains optional; its upstream Skill is not globally registered.")
    print("For hosts without project skill discovery, read AI_START_HERE.md manually.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
