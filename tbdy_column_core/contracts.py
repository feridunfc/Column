"""Immutable, source-bound engineering contracts. Internal units: N, mm, Nmm, MPa.

No ETABS imports, no UI concepts, and no implicit synthetic evidence.
This starter intentionally does NOT define an approved full RC-column design engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
import re


class DemandKind(StrEnum):
    SIGNED_LINEAR_STATIC = "SIGNED_LINEAR_STATIC"
    RESPONSE_SPECTRUM_COMBINED = "RESPONSE_SPECTRUM_COMBINED"
    ENVELOPE = "ENVELOPE"
    UNKNOWN = "UNKNOWN"


class GateStatus(StrEnum):
    NONSWAY_ESTABLISHED = "NONSWAY_ESTABLISHED"
    NONSWAY_NOT_ESTABLISHED = "NONSWAY_NOT_ESTABLISHED"
    EVIDENCE_BLOCKED = "EVIDENCE_BLOCKED"


@dataclass(frozen=True, slots=True)
class EvidenceKey:
    model_sha256: str
    epoch_id: str
    analysis_generation: str
    case_state_id: str
    kind: DemandKind
    unit_system: str = "N-mm-Nmm-MPa"

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[0-9a-fA-F]{64}", self.model_sha256):
            raise ValueError("model_sha256 must be a 64-character SHA-256 hex digest")
        for value in (self.epoch_id, self.analysis_generation, self.case_state_id):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("EvidenceKey fields must be non-empty")
        if self.unit_system != "N-mm-Nmm-MPa":
            raise ValueError("Unsupported unit system: conversion must occur at the adapter boundary")


@dataclass(frozen=True, slots=True)
class ColumnAxialContribution:
    column_id: str
    ndi_n: float  # signed: compression +, tension -; never clamp or omit
    li_mm: float  # normative l_i; NOT assumed equal to story height or joint distance
    evidence: EvidenceKey

    def __post_init__(self) -> None:
        if not self.column_id.strip():
            raise ValueError("Missing column identity")
        if not math.isfinite(self.ndi_n):
            raise ValueError("Non-finite axial demand")
        if not math.isfinite(self.li_mm) or self.li_mm <= 0:
            raise ValueError("Column l_i must be finite and positive")


@dataclass(frozen=True, slots=True)
class StoryStabilityFacts:
    story_id: str
    direction: str  # global X or Y, NOT automatically mapped to local M2/M3
    delta_i_mm: float  # qualified first-order story drift magnitude
    v_fi_n: float  # qualified corresponding story shear magnitude
    expected_column_ids: tuple[str, ...]  # complete story census, not selected columns
    columns: tuple[ColumnAxialContribution, ...]
    evidence: EvidenceKey
    uncracked_sections: bool
    first_order_analysis: bool

    def __post_init__(self) -> None:
        if not self.story_id.strip() or self.direction not in ("X", "Y"):
            raise ValueError("Story identity/direction invalid")
        if not math.isfinite(self.delta_i_mm) or self.delta_i_mm < 0:
            raise ValueError("Qualified drift magnitude must be nonnegative and finite")
        if not math.isfinite(self.v_fi_n) or self.v_fi_n <= 0:
            raise ValueError("Qualified shear magnitude must be finite and positive")


@dataclass(frozen=True, slots=True)
class StoryStabilityResult:
    story_id: str
    direction: str
    rule_id: str
    status: GateStatus
    phi: float | None
    reason: str
    evidence: EvidenceKey
    denominator_column_count: int
    verified_column_count: int


def validate_exact_population(facts: StoryStabilityFacts) -> str | None:
    """Return blocker string unless exact declared story census and state are proven."""
    expected = facts.expected_column_ids
    actual = tuple(col.column_id for col in facts.columns)
    if len(expected) != len(set(expected)) or len(actual) != len(set(actual)):
        return "DUPLICATE_COLUMN_ID"
    if set(expected) != set(actual) or not expected:
        return "STORY_POPULATION_INCOMPLETE"
    if any(col.evidence != facts.evidence for col in facts.columns):
        return "MIXED_MODEL_EPOCH_GENERATION_OR_CASE"
    if facts.evidence.kind != DemandKind.SIGNED_LINEAR_STATIC:
        return "UNQUALIFIED_LOAD_STATE_NO_MODAL_ENVELOPE_REINTERPRETATION"
    if not facts.uncracked_sections or not facts.first_order_analysis:
        return "UNQUALIFIED_ANALYSIS_BASIS"
    if any(col.ndi_n < 0 for col in facts.columns):
        return "TENSION_AXIAL_CASE_REQUIRES_NORMATIVE_REVIEW"
    return None
