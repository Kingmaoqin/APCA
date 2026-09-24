#!/usr/bin/env python3
"""Build the BFCL benchmark adapter from the frozen model roster."""
from __future__ import annotations

import pathlib
from typing import Any

from apca.common import paths
from apca.common.llm_client import load_endpoints


def build_adapters(
    models_path: pathlib.Path = paths.CONFIGS / "models.json",
    *,
    max_step_limit: int = 20,
    bfcl_categories: list[str] | None = None,
    **_ignored: Any,
) -> dict[str, Any]:
    """Return {"bfcl": BfclAdapter, "endpoints": {...}}.

    The APCA / LoopShift-Bench evaluation uses BFCL multi-turn base + missing-parameter tasks.
    Set R9_BFCL_CATEGORIES (comma-separated) to override the category set for every stage.
    """
    import os
    from apca.adapters.bfcl_adapter import BfclAdapter

    if bfcl_categories is None and os.environ.get("R9_BFCL_CATEGORIES"):
        bfcl_categories = [c.strip() for c in os.environ["R9_BFCL_CATEGORIES"].split(",") if c.strip()]

    endpoints = load_endpoints(models_path)
    out: dict[str, Any] = {"endpoints": endpoints}
    out["bfcl"] = BfclAdapter(endpoints=endpoints, max_step_limit=max_step_limit,
                              categories=bfcl_categories)
    return out
