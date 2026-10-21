"""Deterministic passive evidence projection; digest is NOT a signature."""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json

from .engine import FirstPassResult


def report_json(result: FirstPassResult) -> str:
    obj = asdict(result)
    obj["stories"] = [asdict(s) for s in result.stories]
    obj["report_scope"] = "TS500_7_13_STORY_NONS_WAY_GATE_ONLY"
    obj["engineering_release_qualified"] = False
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def report_sha256(result: FirstPassResult) -> str:
    return sha256(report_json(result).encode("utf-8")).hexdigest()
