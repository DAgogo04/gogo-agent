"""gogo-agent — a minimal, transparent, local-first AI agent harness.

Four pillars, one module each:
  harness  → gogo/runtime + gogo/gateway  (scaffolding around the raw LLM)
  loop     → gogo/loop                      (observe → reason → act → repeat)
             gogo/graph                     (opt-in structure around the loop — extends this pillar)
  memory   → gogo/memory                    (procedural / semantic / episodic)
  ops      → gogo/ops + evals/              (trace → eval → gate → release)
"""

__version__ = "0.1.9"
