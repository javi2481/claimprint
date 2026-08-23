#!/usr/bin/env python3
"""Three-arm chat ablation over evals/rag_chat_v1.json (Gate 4).

Live sequential ablation over the same demo_4 / chat_demo_4 stack — not a fully
isolated experimental design. Arms run in order; chat state is shared.

Arms:
  A off    — no IDP chunks, no IDP prompt rules
  B chunks — EEFF IDP chunk only, no prompt rules
  C full   — chunk + IDP prompt rules (current pilot default)

Writes outputs/rag_ablation.json (does not overwrite Gate-3 rag_chat_run.json).
Skip without RAGFlow. Restore inject_mode=full after a successful run.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from push_claims import DEFAULT_CHAT, DEFAULT_DATASET, _run_inject  # noqa: E402
from rag_eval import GOLD, PAUSE_SEC, ask  # noqa: E402
from schemas.rag_chat_score import score_chat_case, summarize_chat  # noqa: E402
from schemas.ragflow_http import (  # noqa: E402
    SKIP_NO_RAGFLOW,
    api,
    load_env,
    ragflow_reachable,
    resolve_api_token,
    rows_of,
)
from schemas.store import load_claims  # noqa: E402

OUT = ROOT / "outputs" / "rag_ablation.json"

ARMS: tuple[tuple[str, str, str], ...] = (
    ("A", "off", "no IDP chunk, no IDP prompt"),
    ("B", "chunks", "IDP chunk only, no prompt rules"),
    ("C", "full", "IDP chunk + prompt rules (pilot default)"),
)


def _chat_id(token: str, wanted: str) -> str | None:
    rows = rows_of(api("GET", "/chats?page_size=100", token), "chats")
    for row in rows:
        if (row.get("name") or "") == wanted:
            return str(row["id"])
    if len(rows) == 1:
        return str(rows[0]["id"])
    return None


def _run_arm(token: str, chat_id: str, gold: dict) -> tuple[dict, list[dict]]:
    runs: list[dict] = []
    scores: list[dict] = []
    for i, case in enumerate(gold["cases"]):
        if i:
            time.sleep(PAUSE_SEC)
        run = ask(token, chat_id, case["question"])
        run["id"] = case["id"]
        runs.append(run)
        scores.append(score_chat_case(case, run))
    return summarize_chat(scores), runs


def main() -> int:
    load_env()
    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    if not ragflow_reachable():
        report = {"skipped": True, "reason": SKIP_NO_RAGFLOW, "arms": []}
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        return 0
    token = resolve_api_token()
    if not token:
        report = {"skipped": True, "reason": SKIP_NO_RAGFLOW, "arms": []}
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        return 0
    claims, _hit = load_claims()
    if not claims:
        print("error: no kernel claims to inject", file=sys.stderr)
        return 1
    wanted = gold.get("assistant") or DEFAULT_CHAT
    chat_id = _chat_id(token, wanted)
    if not chat_id:
        report = {"skipped": True, "reason": "no_chat", "arms": []}
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        return 0

    arm_reports: list[dict] = []
    for arm_id, inject_mode, label in ARMS:
        rc = _run_inject(
            token,
            claims,
            api,
            dataset_name=DEFAULT_DATASET,
            chat_name=DEFAULT_CHAT,
            inject_mode=inject_mode,
        )
        if rc != 0:
            return rc
        time.sleep(5.0)
        summary, cases = _run_arm(token, chat_id, gold)
        arm_reports.append(
            {
                "id": arm_id,
                "inject_mode": inject_mode,
                "label": label,
                "summary": summary,
                "cases": cases,
            }
        )

    _run_inject(
        token,
        claims,
        api,
        dataset_name=DEFAULT_DATASET,
        chat_name=DEFAULT_CHAT,
        inject_mode="full",
    )

    report = {
        "skipped": False,
        "reason": None,
        "assistant": wanted,
        "dataset": DEFAULT_DATASET,
        "arms": arm_reports,
        "restored_inject_mode": "full",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
