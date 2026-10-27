"""DETERMINISTIC EVAL — the rulebook stays short, linked and honest.

The docs are the first thing every contributor and every coding agent reads.
These checks keep what they say true: the README length cap, the links they
route through, the docs index, the examples boundary and the no-emoji rule. A
cap with no check drifts, so every cap in docs/context/conventions.md §9 has a
test here."""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
CONTEXT = DOCS / "context"
README_CAP = 200
RULEBOOK = [
    ROOT / "README.md",
    DOCS / "README.md",
    DOCS / "status.md",
    *(DOCS / name for name in ("getting-started.md", "tour.md", "evals.md", "commands.md", "roadmap.md")),
    *sorted(CONTEXT.glob("*.md")),
    ROOT / "examples" / "README.md",
]

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
# Characters that render as colour emoji: the emoji blocks, anything forced to
# emoji presentation by U+FE0F, and the handful of older symbols that default
# to it (a coffee cup, a check box, a star). Typographic marks such as an
# arrow or a plain star stay allowed.
EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF]"
    "|[☀-➿⬀-⯿]️"
    "|[⌚⌛⏩-⏳☔☕⚡⚪⚫⚽⚾"
    "⛄⛅⛔⛪⛲⛳⛵⛺⛽✅✊✋"
    "✨❌❎❓-❕❗➕-➗➰➿⬛⬜"
    "⭐⭕]"
)


def _local_links(doc: Path) -> list[str]:
    return [
        t for t in LINK.findall(doc.read_text(encoding="utf-8"))
        if not t.startswith(("http://", "https://", "mailto:", "#"))
    ]


def test_readme_stays_a_landing_page():
    """The README answers what this is, why it matters and how to start. It
    grows easily; the long material lives in docs/ now."""
    lines = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    assert len(lines) <= README_CAP, (
        f"README.md is {len(lines)} lines (cap {README_CAP}); move the detail into docs/ "
        "and link it from the Docs table")


def test_rulebook_links_resolve():
    broken = [
        f"{doc.relative_to(ROOT)} -> {target}"
        for doc in RULEBOOK
        for target in _local_links(doc)
        if not (doc.parent / target.split("#", 1)[0]).exists()
    ]
    assert not broken, "broken links:\n" + "\n".join(broken)


def test_every_doc_is_indexed():
    """A doc nobody links to is a doc nobody reads, so docs/README.md lists
    every Markdown file in docs/ and docs/context/."""
    index = DOCS / "README.md"
    linked = {(DOCS / t.split("#", 1)[0]).resolve() for t in _local_links(index)}
    docs = [p for p in (*DOCS.glob("*.md"), *CONTEXT.glob("*.md")) if p != index]
    missing = [str(p.relative_to(ROOT)) for p in docs if p.resolve() not in linked]
    assert not missing, f"add these to docs/README.md: {missing}"


def test_gotchas_are_dated_retirable_and_capped():
    entries = [line for line in (CONTEXT / "gotchas.md").read_text(encoding="utf-8").splitlines()
               if line.startswith("- **[")]
    assert entries, "gotchas.md has no entries in the expected shape"
    assert len(entries) <= 40, f"gotchas.md has {len(entries)} entries; retire some"
    bad = [e[:70] for e in entries
           if not re.match(r"- \*\*\[\d{4}-\d{2}-\d{2}\] ", e) or "_Retire when:" not in e]
    assert not bad, f"each gotcha needs a date and a Retire when: {bad}"


def test_status_is_short_and_dated():
    text = (DOCS / "status.md").read_text(encoding="utf-8")
    assert len(text.splitlines()) <= 120, "status.md is rewritten whole, not appended to"
    assert re.search(r"\*\*Last updated:\*\* \d{4}-\d{2}-\d{2}", text)


def _reaches_outside(node: ast.AST) -> bool:
    """True for an import of examples, or a path literal that points there."""
    if isinstance(node, ast.Import):
        names = [alias.name for alias in node.names]
    elif isinstance(node, ast.ImportFrom) and node.module:
        names = [node.module]
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        names = [node.value.replace("/", ".")]
    else:
        return False
    return any(n == "examples" or n.startswith("examples.") for n in names)


def test_product_and_evals_never_reach_into_examples():
    """The dependency runs one way: product code and the gate never import,
    run or read anything in examples/ (conventions §6)."""
    this = Path(__file__).resolve()
    offenders = sorted({
        str(py.relative_to(ROOT))
        for top in ("gogo", "evals")
        for py in (ROOT / top).rglob("*.py")
        if py.resolve() != this
        for node in ast.walk(ast.parse(py.read_text(encoding="utf-8")))
        if _reaches_outside(node)
    })
    assert not offenders, f"these reach into examples/: {offenders}"


def test_the_package_ships_only_gogo_and_not_the_examples():
    build = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["hatch"]["build"]
    assert build["targets"]["wheel"]["packages"] == ["gogo"]
    excluded = build["targets"]["sdist"]["exclude"]
    assert "examples" in excluded and "docs" in excluded


def test_no_emoji_in_rulebook_or_readme():
    hits = [
        f"{doc.relative_to(ROOT)}:{n}"
        for doc in RULEBOOK
        for n, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1)
        if EMOJI.search(line)
    ]
    assert not hits, f"no emojis in docs prose: {hits}"


def test_no_module_defines_a_top_level_name_twice():
    """A second definition of a module-level name silently replaces the first.

    A large edit once left a duplicated 90-line block in a test file: two
    identical copies of two helpers and two tables. Nothing failed, because
    the second copies were identical — which is exactly why it survived
    review. A tripwire file with dead code in it is a tripwire nobody trusts.

    `ruff --select F811` does not see this: run against that file with the
    duplication present, it exits 0.
    """
    offenders = []
    for path in sorted([*ROOT.glob("gogo/**/*.py"), *ROOT.glob("evals/**/*.py"),
                        *ROOT.glob("scripts/*.py")]):
        seen: dict[str, list[int]] = {}
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                seen.setdefault(node.name, []).append(node.lineno)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        seen.setdefault(target.id, []).append(node.lineno)
        offenders += [f"{path.relative_to(ROOT)}: `{name}` at lines {lines}"
                      for name, lines in seen.items() if len(lines) > 1]
    assert not offenders, (
        "module-level name defined more than once — the later definition wins "
        "and the earlier one is dead:\n  " + "\n  ".join(offenders)
    )
