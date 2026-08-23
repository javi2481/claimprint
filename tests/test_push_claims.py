"""push_claims HTTP mock: EEFF gets a chunk; comunicado does not."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from schemas.claim import (  # noqa: E402
    METRIC_ATRIBUIBLE,
    METRIC_NETO,
    SCOPE_CONSOLIDADO,
    SCOPE_CONTROLANTE,
    Claim,
    identity_key,
)
from schemas.inject import IDP_START  # noqa: E402
from push_claims import INJECT_MODES, _run_inject  # noqa: E402

EEFF = "BYMA_-_EEFF_31-03-2026_VF.pdf"
PRESS = "BYMA_Comunicado_de_Prensa-Resultados-1T26.pdf"


class FakeApi:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.posted: list[str] = []
        self.put_bodies: list[dict] = []

    def __call__(self, method: str, path: str, token: str, data: bytes | None = None) -> dict:
        self.calls.append((method, path))
        if method == "GET" and path.startswith("/datasets?") :
            return {"data": [{"id": "ds1", "name": "demo_4"}]}
        if method == "GET" and path.startswith("/datasets/ds1/documents?") :
            return {
                "data": [
                    {"id": "eeff1", "name": EEFF},
                    {"id": "pr1", "name": PRESS},
                ]
            }
        if method == "GET" and "/chunks" in path:
            return {
                "data": {
                    "chunks": [
                        {"id": "oldg", "content": "Ficha Graph EEFF leftover"},
                    ]
                }
            }
        if method == "GET" and path.startswith("/chats"):
            return {
                "data": [
                    {
                        "id": "chat1",
                        "name": "chat_demo_4",
                        "prompt_config": {"system": "hola {knowledge}"},
                    }
                ]
            }
        if method == "POST" and path.endswith("/chunks"):
            payload = json.loads(data.decode()) if data else {}
            self.posted.append(path)
            assert "Ficha IDP" in payload.get("content", "")
            return {"code": 0}
        if method == "PUT" and path.startswith("/chats/"):
            payload = json.loads(data.decode()) if data else {}
            self.put_bodies.append(payload)
            return {"code": 0}
        if method in {"DELETE", "PUT"}:
            return {"code": 0}
        return {"data": []}


def _claims() -> tuple[Claim, ...]:
    return (
        Claim(
            identity_key=identity_key("BYMA", "2026-03-31", SCOPE_CONSOLIDADO, METRIC_NETO),
            value="21262335",
            period="2026-03-31",
            source_page=4,
            source_text="neto",
            issuer="BYMA",
            scope=SCOPE_CONSOLIDADO,
            metric=METRIC_NETO,
        ),
        Claim(
            identity_key=identity_key("BYMA", "2026-03-31", SCOPE_CONTROLANTE, METRIC_ATRIBUIBLE),
            value="21259769",
            period="2026-03-31",
            source_page=4,
            source_text="controlante",
            issuer="BYMA",
            scope=SCOPE_CONTROLANTE,
            metric=METRIC_ATRIBUIBLE,
        ),
    )


def test_push_claims_posts_before_delete() -> None:
    fake = FakeApi()
    assert _run_inject("tok", _claims(), fake) == 0
    post_idx = next(i for i, (m, _) in enumerate(fake.calls) if m == "POST")
    delete_idx = next(i for i, (m, p) in enumerate(fake.calls) if m == "DELETE" and "eeff1/chunks" in p)
    assert post_idx < delete_idx


def test_push_claims_posts_only_eeff_chunk() -> None:
    fake = FakeApi()
    assert _run_inject("tok", _claims(), fake) == 0
    assert any(path.endswith("/documents/eeff1/chunks") and method == "POST" for method, path in fake.calls)
    assert fake.posted == ["/datasets/ds1/documents/eeff1/chunks"]
    assert not any("pr1" in path and method == "POST" for method, path in fake.calls)
    assert any(method == "DELETE" and "eeff1/chunks" in path for method, path in fake.calls)
    assert any(method == "PUT" and path == "/chats/chat1" for method, path in fake.calls)
    system = fake.put_bodies[-1]["prompt_config"]["system"]
    assert IDP_START in system


def test_push_claims_off_removes_chunks_without_post() -> None:
    fake = FakeApi()
    assert _run_inject("tok", _claims(), fake, inject_mode="off") == 0
    assert fake.posted == []
    assert any(method == "DELETE" and "eeff1/chunks" in path for method, path in fake.calls)
    system = fake.put_bodies[-1]["prompt_config"]["system"]
    assert IDP_START not in system


def test_push_claims_chunks_posts_without_idp_prompt() -> None:
    fake = FakeApi()
    assert _run_inject("tok", _claims(), fake, inject_mode="chunks") == 0
    assert fake.posted == ["/datasets/ds1/documents/eeff1/chunks"]
    system = fake.put_bodies[-1]["prompt_config"]["system"]
    assert IDP_START not in system


def test_inject_modes_tuple() -> None:
    assert INJECT_MODES == ("off", "chunks", "full")



class MultiFakeApi:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.posted: list[str] = []
        self.put_chats: list[str] = []

    def __call__(self, method: str, path: str, token: str, data: bytes | None = None) -> dict:
        self.calls.append((method, path))
        if method == "GET" and path.startswith("/datasets?"):
            return {
                "data": [
                    {"id": "ds1", "name": "demo_4"},
                    {"id": "ds2", "name": "legal_demo"},
                ]
            }
        if method == "GET" and path.startswith("/datasets/ds1/documents?"):
            return {
                "data": [
                    {"id": "eeff1", "name": EEFF},
                    {"id": "pr1", "name": PRESS},
                ]
            }
        if method == "GET" and path.startswith("/datasets/ds2/"):
            raise AssertionError(f"must not read other dataset: {path}")
        if method == "GET" and "/chunks" in path:
            return {"data": {"chunks": []}}
        if method == "GET" and path.startswith("/chats"):
            return {
                "data": [
                    {"id": "chat1", "name": "chat_demo_4", "prompt_config": {"system": "hola {knowledge}"}},
                    {"id": "chat2", "name": "other_chat", "prompt_config": {"system": "x"}},
                ]
            }
        if method == "POST" and path.endswith("/chunks"):
            payload = json.loads(data.decode()) if data else {}
            self.posted.append(path)
            assert 'Ficha IDP' in payload.get("content", "")
            return {"code": 0}
        if method in {"DELETE", "PUT"}:
            if method == "PUT" and path.startswith("/chats/"):
                self.put_chats.append(path)
            if path.startswith("/datasets/ds2"):
                raise AssertionError(f"must not mutate other dataset: {method} {path}")
            return {"code": 0}
        return {"data": []}


def test_push_claims_ignores_other_datasets_and_chats() -> None:
    fake = MultiFakeApi()
    assert _run_inject("tok", _claims(), fake) == 0
    assert fake.posted == ["/datasets/ds1/documents/eeff1/chunks"]
    assert fake.put_chats == ["/chats/chat1"]
    assert not any(method != "GET" and path.startswith("/datasets/ds2") for method, path in fake.calls)


def test_push_claims_fails_if_dataset_missing() -> None:
    class Missing(FakeApi):
        def __call__(self, method: str, path: str, token: str, data: bytes | None = None) -> dict:
            if method == "GET" and path.startswith("/datasets?"):
                return {"data": [{"id": "x", "name": "other"}]}
            return super().__call__(method, path, token, data)

    assert _run_inject("tok", _claims(), Missing()) == 1
