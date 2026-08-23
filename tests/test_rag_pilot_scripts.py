"""RAG pilot scripts skip without stack; no shell=True."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from schemas.ragflow_http import SKIP_NO_RAGFLOW

ROOT = Path(__file__).resolve().parents[1]


def test_scripts_do_not_use_shell_true() -> None:
    for name in ("retrieval_bench.py", "rag_eval.py", "rag_ablation.py", "clear_chat_sessions.py"):
        text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert "shell=True" not in text


def test_bench_and_eval_skip_without_ragflow(monkeypatch) -> None:
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    env["RAGFLOW_URL"] = "http://127.0.0.1:9"
    env.pop("RAGFLOW_API_KEY", None)
    py = sys.executable
    for script in ("retrieval_bench.py", "rag_eval.py", "rag_ablation.py", "clear_chat_sessions.py"):
        proc = subprocess.run(
            [py, str(ROOT / "scripts" / script)],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        payload = json.loads(proc.stdout)
        assert payload["skipped"] is True
        assert payload["reason"] == SKIP_NO_RAGFLOW
