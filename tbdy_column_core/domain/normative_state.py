"""C-15: presence, nonapplicability, missing/unsupported and conflict differ.

Constructing NotRequired is not an applicability proof. A valid applicability
scope receipt MUST be checked through the same evidence-catalog interface.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, TypeVar, TypeAlias
from .identity import EvidenceRef, RuleRef, required
from .analysis_bundle import EvidenceCatalog

T=TypeVar("T")


@dataclass(frozen=True, slots=True)
class Provided(Generic[T]):
    value: T
    evidence_ref: EvidenceRef
    def __post_init__(self):
        if self.value is None or type(self.evidence_ref) is not EvidenceRef:
            raise ValueError("Provided needs value and typed reference; not automatically verified")


@dataclass(frozen=True, slots=True)
class NotRequired:
    requirement_id: str
    rule: RuleRef
    rationale: str
    applicability_evidence: EvidenceRef
    def __post_init__(self):
        required(self.requirement_id,"requirement_id")
        required(self.rationale,"rationale")
        if type(self.rule) is not RuleRef or type(self.applicability_evidence) is not EvidenceRef:
            raise TypeError("NotRequired needs rule and scoped typed evidence")


@dataclass(frozen=True, slots=True)
class Missing:
    field_name: str
    required_by: str
    source_hint: str
    def __post_init__(self):
        for name in ("field_name","required_by","source_hint"):
            required(getattr(self,name),name)


@dataclass(frozen=True, slots=True)
class Unsupported:
    feature_name: str
    method_id: str
    reason: str
    def __post_init__(self):
        for name in ("feature_name","method_id","reason"):
            required(getattr(self,name),name)


@dataclass(frozen=True, slots=True)
class Unresolved:
    subject: str
    conflicting_refs: tuple[str,...]
    reason: str
    def __post_init__(self):
        required(self.subject,"subject")
        required(self.reason,"reason")
        if not self.conflicting_refs:
            raise ValueError("conflicting reference IDs required")
        for item in self.conflicting_refs:
            required(item,"conflicting_ref")


# The two forms of success intentionally differ: Provided only says the
# value exists, NotRequired needs applicable regulatory evidence.
type Outcome[T] = Provided[T] | NotRequired | Missing | Unsupported | Unresolved


def not_required_is_supported(
    outcome: NotRequired, catalog: EvidenceCatalog, *,
    method_id: str, consumer_id: str, input_revision_id: str,
) -> bool:
    """Requires a resolved applicability-specific receipt, not a filled text."""
    if type(outcome) is not NotRequired or type(catalog) is not EvidenceCatalog:
        raise TypeError("typed inputs required")
    return len([r for r in catalog.scopes if
                r.evidence == outcome.applicability_evidence and
                r.role == "APPLICABILITY:" + outcome.requirement_id and
                r.method_id == method_id and r.consumer_id == consumer_id and
                r.input_revision_id == input_revision_id and
                r.evidence.input_revision.revision == input_revision_id and
                r.applicability_rule == outcome.rule]) == 1
