"""Explicit regulatory-input knowledge states. Never infer NotRequired from absence."""
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


def nonblank(s, name):
    if not isinstance(s, str) or not s.strip():
        raise ValueError(f"{name} requires nonblank reference")


@dataclass(frozen=True, slots=True)
class Provided(Generic[T]):
    value: T
    source_ref: str
    verification_ref: str
    def __post_init__(self):
        if self.value is None:
            raise ValueError("Provided cannot carry None")
        for name in ("source_ref", "verification_ref"):
            nonblank(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class NotRequired:
    rule_ref: str
    reason: str
    applicability_evidence_ref: str
    def __post_init__(self):
        for name in ("rule_ref", "reason", "applicability_evidence_ref"):
            nonblank(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class Missing:
    field_name: str
    required_by: str
    missing_source: str
    def __post_init__(self):
        for name in ("field_name", "required_by", "missing_source"):
            nonblank(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class Unsupported:
    feature_name: str
    method_id: str
    reason: str
    def __post_init__(self):
        for name in ("feature_name", "method_id", "reason"):
            nonblank(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class Unresolved:
    subject: str
    conflicting_refs: tuple[str, ...]
    reason: str
    def __post_init__(self):
        nonblank(self.subject, "subject")
        nonblank(self.reason, "reason")
        if not self.conflicting_refs or any(not isinstance(x, str) or not x.strip() for x in self.conflicting_refs):
            raise ValueError("Unresolved requires conflicting evidence references")
