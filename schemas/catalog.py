"""Recipe catalog: one JSON file per document type. UNKNOWN is not a recipe."""

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECIPES_DIR = ROOT / "recipes"


@dataclass(frozen=True)
class Recipe:
    id: str
    description: str
    extract: bool
    schema_path: str | None
    page_select_keywords: tuple[str, ...]
    gold: dict[str, dict[str, str]]

    def schema_cls(self) -> type | None:
        if not self.schema_path:
            return None
        module_name, _, attr = self.schema_path.rpartition(".")
        module = importlib.import_module(module_name)
        return getattr(module, attr)


def _load_file(path: Path) -> Recipe:
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    rid = str(raw["id"])
    if rid.upper() == "UNKNOWN":
        raise ValueError(f"{path.name}: UNKNOWN is a classifier class, not a recipe file")
    return Recipe(
        id=rid,
        description=str(raw["description"]).strip(),
        extract=bool(raw.get("extract", False)),
        schema_path=raw.get("schema") or None,
        page_select_keywords=tuple(raw.get("page_select_keywords") or ()),
        gold={str(k): dict(v) for k, v in (raw.get("gold") or {}).items()},
    )


def load_recipes(directory: Path | None = None) -> dict[str, Recipe]:
    folder = directory or RECIPES_DIR
    found: dict[str, Recipe] = {}
    for path in sorted(folder.glob("*.json")):
        recipe = _load_file(path)
        if recipe.id in found:
            raise ValueError(f"duplicate recipe id: {recipe.id}")
        found[recipe.id] = recipe
    if not found:
        raise ValueError("catalog empty")
    return found


def classifier_labels(recipes: dict[str, Recipe] | None = None) -> tuple[str, ...]:
    catalog = recipes or load_recipes()
    return tuple(sorted(catalog)) + ("UNKNOWN",)
