"""B6 deterministic, local integrity receipts for a *finished* section result.

No source authorization, signature, physics recomputation or normative PASS.
The receipt is a digest of two finished report byte streams. A party who may
replace both content and the hashes can forge a self-consistent package.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from json import dumps, loads, JSONDecodeError

from ..domain.section_requests import SectionCapacityResult
from .section_report import section_report_json, section_report_html


RECEIPT_SCHEMA = "column.section.report-receipt.sha256.v1"
REPORT_SCHEMA = "column.section.numeric.v1.3-b1"


def _hex_digest(value: str) -> bool:
    return type(value) is str and len(value) == 64 and all(
        digit in "0123456789abcdef" for digit in value
    )


def _digest(data: str) -> str:
    return sha256(data.encode("utf-8")).hexdigest()


def _canonical_json(obj: object) -> str:
    return dumps(obj, sort_keys=True, ensure_ascii=False,
                 allow_nan=False, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class SectionOutputReceipt:
    """Self-consistency evidence, NOT a signed or independently trusted record."""

    schema: str
    input_sha256: str
    result_json_sha256: str
    report_html_sha256: str
    result_status: str
    result_schema: str
    kernel_ref: str

    def __post_init__(self) -> None:
        if self.schema != RECEIPT_SCHEMA:
            raise ValueError("unsupported section receipt schema")
        for field in ("input_sha256", "result_json_sha256", "report_html_sha256"):
            if not _hex_digest(getattr(self, field)):
                raise ValueError(f"{field} must be lowercase SHA-256")
        for field in ("result_status", "result_schema", "kernel_ref"):
            value = getattr(self, field)
            if type(value) is not str or not value.strip():
                raise ValueError(f"{field} must be a nonblank string")


@dataclass(frozen=True, slots=True)
class SealedSectionReport:
    """Immutable snapshot of the exact JSON/HTML that were individually hashed."""

    receipt: SectionOutputReceipt
    result_json: str
    report_html: str

    def __post_init__(self) -> None:
        if type(self.receipt) is not SectionOutputReceipt:
            raise TypeError("typed SectionOutputReceipt required")
        if type(self.result_json) is not str or type(self.report_html) is not str:
            raise TypeError("JSON and HTML text snapshots required")


@dataclass(frozen=True, slots=True)
class ReportIntegrityCheck:
    """Byte consistency only; never an engineering approval or source proof."""

    bytes_match: bool
    issues: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.bytes_match) is not bool or type(self.issues) is not tuple:
            raise TypeError("typed integrity result required")
        if self.bytes_match != (not self.issues):
            raise ValueError("integrity status must agree with issues")


def seal_section_report(result: SectionCapacityResult) -> SealedSectionReport:
    """Capture existing passive projections once; no second solver invocation."""
    if type(result) is not SectionCapacityResult:
        raise TypeError("typed SectionCapacityResult required")
    json_text = section_report_json(result)
    html_text = section_report_html(result)
    receipt = SectionOutputReceipt(
        schema=RECEIPT_SCHEMA,
        input_sha256=result.input_fingerprint.sha256,
        result_json_sha256=_digest(json_text),
        report_html_sha256=_digest(html_text),
        result_status=result.status.value,
        result_schema=REPORT_SCHEMA,
        kernel_ref=result.kernel_ref,
    )
    return SealedSectionReport(receipt, json_text, html_text)


def section_output_receipt_json(receipt: SectionOutputReceipt) -> str:
    if type(receipt) is not SectionOutputReceipt:
        raise TypeError("typed SectionOutputReceipt required")
    return _canonical_json({
        "schema": receipt.schema,
        "input_sha256": receipt.input_sha256,
        "result_json_sha256": receipt.result_json_sha256,
        "report_html_sha256": receipt.report_html_sha256,
        "result_status": receipt.result_status,
        "result_schema": receipt.result_schema,
        "kernel_ref": receipt.kernel_ref,
        "interpretation": (
            "Local self-consistency of declared input and saved JSON/HTML bytes; "
            "not a signature, external provenance proof or TS500/TBDY approval"
        ),
    })


def verify_sealed_section_report(package: SealedSectionReport) -> ReportIntegrityCheck:
    """Check receipt and captured bytes offline; no source record or physics access."""
    if type(package) is not SealedSectionReport:
        raise TypeError("typed SealedSectionReport required")
    receipt = package.receipt
    issues: list[str] = []
    if _digest(package.result_json) != receipt.result_json_sha256:
        issues.append("RESULT_JSON_BYTES_CHANGED")
    if _digest(package.report_html) != receipt.report_html_sha256:
        issues.append("REPORT_HTML_BYTES_CHANGED")

    # Reject noncanonical JSON (including reformatting) and nonfinite constants,
    # even if someone recomputes a matching SHA-256 over the altered bytes.
    try:
        parsed = loads(
            package.result_json,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")),
        )
        if type(parsed) is not dict or _canonical_json(parsed) != package.result_json:
            issues.append("NONCANONICAL_RESULT_JSON")
    except (JSONDecodeError, ValueError, TypeError, OverflowError):
        parsed = None
        issues.append("INVALID_RESULT_JSON")

    if type(parsed) is dict:
        identity = parsed.get("input_fingerprint")
        if (type(identity) is not dict or
                identity.get("sha256") != receipt.input_sha256):
            issues.append("DECLARED_INPUT_DIGEST_MISMATCH")
        if parsed.get("status") != receipt.result_status:
            issues.append("RESULT_STATUS_MISMATCH")
        if parsed.get("schema") != receipt.result_schema:
            issues.append("RESULT_SCHEMA_MISMATCH")
        if parsed.get("kernel_ref") != receipt.kernel_ref:
            issues.append("KERNEL_IDENTITY_MISMATCH")
        if parsed.get("full_column_design_pass") is not False:
            issues.append("UNSUPPORTED_COLUMN_APPROVAL_CLAIM")
    return ReportIntegrityCheck(not issues, tuple(issues))
