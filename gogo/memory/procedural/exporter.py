"""`gogo skill export`: carry Gogo's skills to the other agents you use.

A skill is a folder holding a SKILL.md, and Claude Code, Codex and Muse Code
read that same format. This copies every skill Gogo loads (the bundled ones,
the contributed ones and the ones in GOGO_HOME/skills) into another agent's
skills folder:

    gogo skill export                      ~/.claude/skills/<name>/
    gogo skill export --to claude,codex    and ~/.codex/skills/<name>/
    gogo skill export --project            ./.claude/skills/<name>/, which Muse Code also reads
    gogo skill export --force              replace a copy that has changed since

A copy that differs from Gogo's is kept unless you pass --force, because it may
hold edits made in the other agent. Some skills lean on Gogo's own tools (a
calendar skill calls create_event); in another agent they arrive as
instructions without those tools behind them.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

# target name -> the folder under your home (or the project) that holds `skills/`
TARGETS = {"claude": ".claude", "codex": ".codex"}


def _skills(home: Path) -> list:
    """Every skill Gogo loads, one per name. A skill in GOGO_HOME/skills wins
    over a bundled one of the same name, as it does when Gogo loads them."""
    from gogo.memory import bundled_skill_dirs
    from gogo.memory.procedural.loader import SkillLoader

    dirs = [*bundled_skill_dirs(), home / "skills"]
    roots = {d.resolve() for d in dirs}
    by_name = {}
    for skill in SkillLoader(dirs).skills:
        folder = skill.path.parent.resolve()
        # A SKILL.md sitting directly in a skills root would make its "folder"
        # the whole root, and copying that would copy every other skill too.
        if folder in roots or "_incoming" in folder.parts:
            continue
        by_name[skill.name] = skill
    return list(by_name.values())


def _files(folder: Path) -> dict[Path, bytes]:
    return {p.relative_to(folder): p.read_bytes() for p in folder.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.name != ".DS_Store"}


def export(targets: list[str], home: Path, base: Path, force: bool = False) -> list[str]:
    """Copy each skill folder to base/<target>/skills/<name>/. One line per copy."""
    lines = []
    for target in targets:
        root = base / TARGETS[target] / "skills"
        for skill in _skills(home):
            src, dest = skill.path.parent, root / skill.name
            if dest.exists():
                if _files(src) == _files(dest):
                    lines.append(f"  unchanged   {dest}")
                    continue
                if not force:
                    lines.append(f"  kept yours  {dest} (it differs; --force replaces it)")
                    continue
                shutil.rmtree(dest)
            shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
            lines.append(f"  copied      {dest}")
    return lines


def cli_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="gogo skill export",
        description="Copy Gogo's skills into another agent's skills folder.")
    parser.add_argument("--to", default="claude", help="claude, codex, or both: claude,codex")
    parser.add_argument("--project", action="store_true",
                        help="write under ./.claude or ./.codex in this folder instead of your home")
    parser.add_argument("--force", action="store_true", help="replace copies that differ")
    args = parser.parse_args(argv)

    targets = [t.strip().lower() for t in args.to.split(",") if t.strip()]
    if "memory" in targets:
        print("Exporting skills to Gogo Memory is not available yet: Gogo Memory is adding "
              "a place for skills first. For now: --to claude,codex")
        return 1
    unknown = [t for t in targets if t not in TARGETS]
    if unknown or not targets:
        print(f"Unknown target: {', '.join(unknown) or '(none)'}. Choose from: {', '.join(TARGETS)}")
        return 1

    from gogo.config import load_settings

    lines = export(targets, load_settings().home, Path.cwd() if args.project else Path.home(),
                   force=args.force)
    print("\n".join(lines) if lines else "No skills found to export.")
    return 0
