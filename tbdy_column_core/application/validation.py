"""B3: explicitly typed validation for public, possibly untrusted inputs.

This is a non-throwing validation boundary for caller input and declared
unsupported pilot features. calculate_section(problem) preserves its
C-19 strict typed programming contract; internal invariant errors are never
swallowed or disguised as engineering results.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from ..domain.section_requests import (
    SectionCapacityProblem, SectionCapacityResult, SectionStatus,
)
from ..engineering.section_adapter import UnsupportedSectionMaterial,SectionKernelAdapter
from ..engineering.section_solver import SectionSolver


class ValidationStatus(StrEnum):
    READY="READY"
    INVALID_INPUT="INVALID_INPUT"
    UNSUPPORTED_INPUT="UNSUPPORTED_INPUT"


@dataclass(frozen=True,slots=True)
class SectionInputValidation:
    status: ValidationStatus
    issues: tuple[str,...]
    def __post_init__(self):
        if type(self.status) is not ValidationStatus:
            raise TypeError("typed validation status required")
        if (self.status==ValidationStatus.READY)!=(not self.issues):
            raise ValueError("validation success must have no issues")


@dataclass(frozen=True,slots=True)
class ValidatedSectionOutcome:
    validation: SectionInputValidation
    result: SectionCapacityResult | None
    def __post_init__(self):
        if type(self.validation) is not SectionInputValidation:
            raise TypeError("SectionInputValidation required")
        if (self.validation.status==ValidationStatus.READY)!=(self.result is not None):
            raise ValueError("invalid or unsupported input never has calculated result")
        if self.result is not None and type(self.result) is not SectionCapacityResult:
            raise TypeError("SectionCapacityResult required")


def validate_section_problem(candidate: object)->SectionInputValidation:
    """No constructor repair; receives an already-constructed typed object."""
    if type(candidate) is not SectionCapacityProblem:
        return SectionInputValidation(ValidationStatus.INVALID_INPUT,
                                      ("EXPECTED_SECTION_CAPACITY_PROBLEM",))
    if candidate.frame_model_contract.reference!="SECTION_GEOMETRIC_CENTROID":
        return SectionInputValidation(ValidationStatus.UNSUPPORTED_INPUT,
                                     ("UNSUPPORTED_FRAME_REFERENCE",))
    if candidate.frame_model_contract.axial_sign.value!="F1_COMPRESSION_POSITIVE":
        return SectionInputValidation(ValidationStatus.UNSUPPORTED_INPUT,
                                     ("UNSUPPORTED_AXIAL_SIGN_CONVENTION",))
    adapter=SectionKernelAdapter(candidate.section,candidate.frame_model_contract)
    try:
        adapter.prepare_material()
    except UnsupportedSectionMaterial:
        # The raw source labels/strengths remain available in candidate.
        return SectionInputValidation(ValidationStatus.UNSUPPORTED_INPUT,
                                     ("UNSUPPORTED_SECTION_MATERIAL_LAW",))
    return SectionInputValidation(ValidationStatus.READY,())


def calculate_section_validated(candidate: object)->ValidatedSectionOutcome:
    """Typed user-input errors become validation outcome, never false PASS.

    Internal coding defects continue to raise on SectionSolver execution.
    Do not wrap bare Exceptions here.
    """
    validation=validate_section_problem(candidate)
    if validation.status!=ValidationStatus.READY:
        return ValidatedSectionOutcome(validation,None)
    return ValidatedSectionOutcome(validation,SectionSolver().calculate(candidate))
