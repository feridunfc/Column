"""B6: deterministic *unsigned* result-payload integrity envelopes.

This is a byte-canonical SHA-256 receipt for the section result projection,
not a signature, trusted timestamp, execution attestation, or regulatory
approval. Anyone may rewrite both payload and digest. Independent trust in
an output hash requires an external authenticated channel/anchor.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from hmac import compare_digest
import json
from math import isfinite

from .section_report import section_payload
from ..domain.section_requests import SectionCapacityResult, CalculationInputFingerprint

RECEIPT_SCHEMA = "column.section.result-receipt.sha256.v1"
PAYLOAD_SCHEMA = "column.section.numeric.v1.3-b1"
HEX = frozenset("0123456789abcdef")


def _canonical_json_bytes(obj: object) -> bytes:
    """Stable UTF-8 JSON with explicit NaN/Infinity exclusion."""
    return json.dumps(obj,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False,allow_nan=False).encode("utf-8")


def _valid_sha256(value: object) -> bool:
    return type(value) is str and len(value)==64 and all(c in HEX for c in value)


def receipt_for_payload(payload: dict) -> dict:
    """Bind exactly the passive section payload, including N/M and issue status.

    The embedded input fingerprint is copied as a declared reference; it
    is *not* recomputed from source data in the reporting layer.
    """
    if type(payload) is not dict or payload.get("schema") != PAYLOAD_SCHEMA:
        raise ValueError("unsupported section payload schema")
    input_ref=payload.get("input_fingerprint")
    if type(input_ref) is not dict or input_ref.get("schema") != CalculationInputFingerprint.SCHEMA:
        raise ValueError("unsupported declared-input fingerprint")
    input_sha=input_ref.get("sha256")
    if not _valid_sha256(input_sha):
        raise ValueError("invalid declared-input SHA256")
    return {
        "schema":RECEIPT_SCHEMA,
        "algorithm":"SHA-256",
        "payload_schema":PAYLOAD_SCHEMA,
        "input_sha256":input_sha,
        "payload_sha256":sha256(_canonical_json_bytes(payload)).hexdigest(),
        "meaning":"unsigned integrity only; no execution or normative approval",
    }


def section_report_bundle_json(result: SectionCapacityResult) -> str:
    """One source result -> canonical JSON payload and explicit digest."""
    payload=section_payload(result)
    return _canonical_json_bytes({
        "payload":payload,
        "receipt":receipt_for_payload(payload)
    }).decode("utf-8")


class ReceiptCheckStatus(StrEnum):
    MATCH="MATCH"
    MISMATCH="MISMATCH"
    MALFORMED="MALFORMED"
    UNSUPPORTED="UNSUPPORTED"


@dataclass(frozen=True,slots=True)
class ReceiptCheck:
    status: ReceiptCheckStatus
    issues: tuple[str,...]
    observed_payload_sha256: str | None
    declared_payload_sha256: str | None
    def __post_init__(self):
        if type(self.status) is not ReceiptCheckStatus:
            raise TypeError("ReceiptCheckStatus required")
        if type(self.issues) is not tuple or not self.issues:
            if self.status!=ReceiptCheckStatus.MATCH:
                raise ValueError("nonmatching receipt needs explicit issues")
        if self.status==ReceiptCheckStatus.MATCH and self.issues:
            raise ValueError("matching receipt cannot have issues")
        if self.observed_payload_sha256 is not None and not _valid_sha256(self.observed_payload_sha256):
            raise ValueError("invalid observed digest")
        if self.declared_payload_sha256 is not None and not _valid_sha256(self.declared_payload_sha256):
            raise ValueError("invalid declared digest")


def _unique_object(pairs):
    """Prevent ambiguous duplicate JSON keys from hiding altered fields."""
    out={}
    for k,v in pairs:
        if k in out:
            raise ValueError("duplicate JSON key: "+k)
        out[k]=v
    return out


def _invalid_constant(value):
    raise ValueError("non-finite JSON constant: "+value)


def verify_section_bundle_json(serialized: str) -> ReceiptCheck:
    """Check local structural integrity; do NOT authenticate authorship.

    Unknown receipt versions fail closed. A MATCH means only that the
    supplied payload recomputes to the supplied unsigned digest.
    """
    if type(serialized) is not str:
        return ReceiptCheck(ReceiptCheckStatus.MALFORMED,("EXPECTED_JSON_STRING",),None,None)
    try:
        bundle=json.loads(serialized,object_pairs_hook=_unique_object,
                          parse_constant=_invalid_constant)
    except (ValueError,TypeError,OverflowError,RecursionError):
        return ReceiptCheck(ReceiptCheckStatus.MALFORMED,("INVALID_OR_AMBIGUOUS_JSON",),None,None)
    if type(bundle) is not dict or set(bundle)!={"payload","receipt"}:
        return ReceiptCheck(ReceiptCheckStatus.MALFORMED,("INVALID_BUNDLE_SHAPE",),None,None)
    payload=bundle["payload"]
    receipt=bundle["receipt"]
    if type(payload) is not dict or type(receipt) is not dict:
        return ReceiptCheck(ReceiptCheckStatus.MALFORMED,("INVALID_CONTENT_SHAPE",),None,None)
    if payload.get("schema")!=PAYLOAD_SCHEMA or receipt.get("schema")!=RECEIPT_SCHEMA:
        return ReceiptCheck(ReceiptCheckStatus.UNSUPPORTED,("UNSUPPORTED_RECEIPT_OR_PAYLOAD_SCHEMA",),None,None)
    required={"schema","algorithm","payload_schema","input_sha256",
              "payload_sha256","meaning"}
    if set(receipt)!=required or receipt.get("algorithm")!="SHA-256" or receipt.get("payload_schema")!=PAYLOAD_SCHEMA or receipt.get("meaning")!="unsigned integrity only; no execution or normative approval":
        return ReceiptCheck(ReceiptCheckStatus.UNSUPPORTED,("UNSUPPORTED_RECEIPT_CONTRACT",),None,None)
    declared=receipt.get("payload_sha256")
    if not _valid_sha256(declared) or not _valid_sha256(receipt.get("input_sha256")):
        return ReceiptCheck(ReceiptCheckStatus.MALFORMED,("INVALID_RECEIPT_DIGEST",),None,None)
    input_ref=payload.get("input_fingerprint")
    if type(input_ref) is not dict or input_ref.get("schema")!=CalculationInputFingerprint.SCHEMA:
        return ReceiptCheck(ReceiptCheckStatus.UNSUPPORTED,("UNSUPPORTED_INPUT_IDENTITY_SCHEMA",),None,declared)
    if not _valid_sha256(input_ref.get("sha256")):
        return ReceiptCheck(ReceiptCheckStatus.MALFORMED,("INVALID_INPUT_DIGEST",),None,declared)
    try:
        observed=sha256(_canonical_json_bytes(payload)).hexdigest()
    except (ValueError,TypeError,OverflowError,RecursionError):
        return ReceiptCheck(ReceiptCheckStatus.MALFORMED,("UNCANONICALIZABLE_PAYLOAD",),None,declared)
    errors=[]
    if not compare_digest(observed,declared):
        errors.append("RESULT_PAYLOAD_SHA256_MISMATCH")
    if not compare_digest(input_ref["sha256"],receipt["input_sha256"]):
        errors.append("INPUT_LINK_SHA256_MISMATCH")
    return ReceiptCheck(
        ReceiptCheckStatus.MISMATCH if errors else ReceiptCheckStatus.MATCH,
        tuple(errors),observed,declared
    )
