"""B6: deterministic receipt for a passive, already-calculated section report.

Binds every visible numerical result/status/evidence/policy field to the B5
input digest through a reproducible SHA-256 checksum. Not signed, trusted,
or an attestation that the physics was executed correctly. No filesystem IO.
"""
from __future__ import annotations

from hashlib import sha256
from hmac import compare_digest
import json
from typing import Any

RECEIPT_SCHEMA = "column.section.output.sha256.v1"
REPORT_SCHEMA = "column.section.numeric.v1.3-b1"
INPUT_SCHEMA = "column.section.input.sha256.v1"


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    if type(payload) is not dict or "output_receipt" in payload:
        raise ValueError("receipt hashes exactly the payload without itself")
    return json.dumps(payload,sort_keys=True,ensure_ascii=False,
                      allow_nan=False,separators=(",",":")).encode("utf-8")


def _is_digest(value: object) -> bool:
    return type(value) is str and len(value)==64 and all(
        ch in "0123456789abcdef" for ch in value)


def output_receipt_for_payload(payload: dict[str, Any]) -> dict[str,str]:
    """Attach input digest + output digest without any N/M recomputation."""
    if type(payload) is not dict or payload.get("schema")!=REPORT_SCHEMA:
        raise ValueError("unsupported numeric section report schema")
    inp=payload.get("input_fingerprint")
    if type(inp) is not dict or inp.get("schema")!=INPUT_SCHEMA or not _is_digest(inp.get("sha256")):
        raise ValueError("missing typed B5 declared input digest")
    result_digest=sha256(_canonical_bytes(payload)).hexdigest()
    return {
        "schema": RECEIPT_SCHEMA,
        "sha256":result_digest,
        "input_sha256":inp["sha256"],
        "meaning":"unsigned content checksum; not source authentication, execution proof or code approval",
    }


def verify_section_report_json(report: str) -> bool:
    """Check that the report's *stored* receipt matches its serialized content.

    FALSE on a missing/malformed/damaged receipt, status, issue, geometry,
    input fingerprint, policy, or state. An adversary who can rewrite the
    payload can also recompute an unsigned digest: do not use as authenticity
    or engineering approval evidence.
    """
    if type(report) is not str:
        return False
    try:
        # Reject ambiguous JSON objects that repeat a key.
        def unique_object(pairs):
            record={}
            for k,v in pairs:
                if k in record:
                    raise ValueError("duplicate JSON key")
                record[k]=v
            return record
        parsed=json.loads(report,object_pairs_hook=unique_object)
        if type(parsed) is not dict or "output_receipt" not in parsed:
            return False
        receipt=parsed.pop("output_receipt")
        if type(receipt) is not dict or set(receipt)!={"schema","sha256","input_sha256","meaning"}:
            return False
        if receipt["schema"]!=RECEIPT_SCHEMA or not _is_digest(receipt["sha256"]):
            return False
        expected=output_receipt_for_payload(parsed)
        # No supplied receipt field can be silently ignored.
        return all(
            type(receipt[k]) is str and compare_digest(receipt[k],expected[k])
            for k in expected
        )
    except (TypeError,ValueError,OverflowError,RecursionError):
        return False
