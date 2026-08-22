#!/usr/bin/env python3
"""Delete RAGFlow chat sessions (e.g. after rag_eval).

Each POST /chats/{id}/completions opens a UI session. Safe to run after pilot runs.
Skip without RAGFlow. Not identity pytest.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from schemas.ragflow_http import (  # noqa: E402
    SKIP_NO_RAGFLOW,
    api,
    load_env,
    ragflow_reachable,
    resolve_api_token,
    rows_of,
)

DEFAULT_CHAT = os.environ.get("CLAIMPRINT_CHAT", "chat_demo_4")
# RAGFlow returns an empty list when page_size is too large (e.g. 500).
SESSION_PAGE = 50


def _chat_id(token: str, wanted: str) -> str | None:
    rows = rows_of(api("GET", "/chats?page_size=100", token), "chats")
    for row in rows:
        if (row.get("name") or "") == wanted:
            return str(row["id"])
    if len(rows) == 1:
        return str(rows[0]["id"])
    return None


def _session_ids(token: str, chat_id: str) -> list[str]:
    ids: list[str] = []
    page = 1
    while True:
        rows = rows_of(
            api(
                "GET",
                f"/chats/{chat_id}/sessions?page={page}&page_size={SESSION_PAGE}",
                token,
            )
        )
        ids.extend(str(row["id"]) for row in rows)
        if len(rows) < SESSION_PAGE:
            break
        page += 1
    return ids


def _delete_sessions(token: str, chat_id: str, ids: list[str]) -> None:
    for i in range(0, len(ids), SESSION_PAGE):
        batch = ids[i : i + SESSION_PAGE]
        api(
            "DELETE",
            f"/chats/{chat_id}/sessions",
            token,
            json.dumps({"ids": batch}).encode(),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Clear RAGFlow chat sessions for an assistant.")
    parser.add_argument(
        "--chat",
        default=DEFAULT_CHAT,
        help=f"Assistant name (default: {DEFAULT_CHAT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report session count without deleting",
    )
    args = parser.parse_args()

    load_env()
    if not ragflow_reachable():
        report = {
            "skipped": True,
            "reason": SKIP_NO_RAGFLOW,
            "chat": args.chat,
            "sessions": 0,
            "deleted": 0,
        }
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        return 0

    token = resolve_api_token()
    if not token:
        report = {
            "skipped": True,
            "reason": SKIP_NO_RAGFLOW,
            "chat": args.chat,
            "sessions": 0,
            "deleted": 0,
        }
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        return 0

    chat_id = _chat_id(token, args.chat)
    if not chat_id:
        report = {
            "skipped": True,
            "reason": "no_chat",
            "chat": args.chat,
            "sessions": 0,
            "deleted": 0,
        }
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        return 1

    ids = _session_ids(token, chat_id)
    count = len(ids)
    if args.dry_run:
        report = {
            "skipped": False,
            "dry_run": True,
            "chat": args.chat,
            "chat_id": chat_id,
            "sessions": count,
            "deleted": 0,
        }
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        return 0

    deleted = 0
    if not args.dry_run and count:
        _delete_sessions(token, chat_id, ids)
        deleted = count
        remaining = len(_session_ids(token, chat_id))
        if remaining:
            sys.stderr.write(f"warning: {remaining} sessions remain after delete\n")

    report = {
        "skipped": False,
        "dry_run": False,
        "chat": args.chat,
        "chat_id": chat_id,
        "sessions": count,
        "deleted": deleted,
    }
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
