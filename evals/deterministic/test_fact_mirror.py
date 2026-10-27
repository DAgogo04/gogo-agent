"""DETERMINISTIC EVAL — every fact is also a file (spec 003, gogo-agent#253).

Gogo was the one agent whose memory never reached Gogo Memory. The importer
other agents use reads files, one memory per file, the way Claude Code keeps
one file per fact. So after every turn Gogo writes each fact to
<home>/memory/<id>.md. Example carried through: "Acme cut its price to $19".
"""

from __future__ import annotations

from pathlib import Path

from gogo.config import Settings
from gogo.db import connect
from gogo.memory import Memory


def _memory(tmp_path: Path) -> Memory:
    settings = Settings(home=tmp_path)
    settings.ensure_home()
    return Memory(connect(tmp_path), settings, client=None)


def _add_fact(memory: Memory, subject: str, content: str) -> int:
    cur = memory.conn.execute("INSERT INTO facts (subject, content) VALUES (?, ?)", (subject, content))
    memory.conn.commit()
    return cur.lastrowid


def test_each_fact_becomes_one_file(tmp_path):
    memory = _memory(tmp_path)
    acme = _add_fact(memory, "acme", "Acme cut its price to $19.")
    sam = _add_fact(memory, "sam", "Sam prefers morning meetings.")
    memory.export_markdown()
    acme_file = (tmp_path / "memory" / f"{acme}.md").read_text(encoding="utf-8")
    assert acme_file.startswith("---\nsubject: acme\nsource: user\ncreated_at: ")
    assert acme_file.endswith("---\nAcme cut its price to $19.\n")
    assert "Sam prefers morning meetings." in (tmp_path / "memory" / f"{sam}.md").read_text()
    assert sorted(p.name for p in (tmp_path / "memory").iterdir()) == sorted([f"{acme}.md", f"{sam}.md"])


def test_an_unchanged_fact_is_not_rewritten(tmp_path):
    memory = _memory(tmp_path)
    acme = _add_fact(memory, "acme", "Acme cut its price to $19.")
    memory.export_markdown()
    path = tmp_path / "memory" / f"{acme}.md"
    before, mtime = path.read_bytes(), path.stat().st_mtime_ns
    memory.export_markdown()
    assert path.read_bytes() == before
    assert path.stat().st_mtime_ns == mtime, "an unchanged file is not touched, so a re-import is free"


def test_an_edited_fact_rewrites_its_file(tmp_path):
    memory = _memory(tmp_path)
    acme = _add_fact(memory, "acme", "Acme cut its price to $19.")
    memory.export_markdown()
    memory.conn.execute("UPDATE facts SET content = ? WHERE id = ?", ("Acme cut its price to $15.", acme))
    memory.conn.commit()
    memory.export_markdown()
    assert (tmp_path / "memory" / f"{acme}.md").read_text().endswith("Acme cut its price to $15.\n")


def test_a_deleted_fact_loses_its_file_and_nothing_else_is_touched(tmp_path):
    memory = _memory(tmp_path)
    acme = _add_fact(memory, "acme", "Acme cut its price to $19.")
    sam = _add_fact(memory, "sam", "Sam prefers morning meetings.")
    memory.export_markdown()
    (tmp_path / "memory" / "my-notes.md").write_text("mine")
    memory.conn.execute("DELETE FROM facts WHERE id = ?", (sam,))
    memory.conn.commit()
    memory.export_markdown()
    names = sorted(p.name for p in (tmp_path / "memory").iterdir())
    assert names == sorted([f"{acme}.md", "my-notes.md"])


def test_no_episode_is_written_as_a_fact_file(tmp_path):
    memory = _memory(tmp_path)
    memory.conn.execute(
        "INSERT INTO episodes (happened_at, summary) VALUES ('2026-10-01', 'Talked about the treg video.')")
    memory.conn.commit()
    _add_fact(memory, "acme", "Acme cut its price to $19.")
    memory.export_markdown()
    for path in (tmp_path / "memory").iterdir():
        assert "treg video" not in path.read_text()


def test_a_subject_with_a_line_break_stays_one_line_of_front_matter(tmp_path):
    memory = _memory(tmp_path)
    fact = _add_fact(memory, "acme\ncorp", "Acme cut its price to $19.")
    memory.export_markdown()
    assert "subject: acme corp\n" in (tmp_path / "memory" / f"{fact}.md").read_text()


