"""Passive S1 reporting: no independent engineering re-calculation."""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json

from .s1 import S1Result


def s1_report_json(result: S1Result) -> str:
    record = asdict(result)
    record["report_kind"] = "PRELIMINARY_SIGNED_STATIC_LONGITUDINAL_PMM"
    record["engineering_release_qualified"] = False
    return json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def s1_report_sha256(result: S1Result) -> str:
    return sha256(s1_report_json(result).encode("utf-8")).hexdigest()
