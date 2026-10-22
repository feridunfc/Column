"""C-24: independent applicability/execution/compliance/coverage/freshness."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from .identity import RuleRef,required
from .quantities import Quantity,finite_real


class Applicability(StrEnum):
    APPLIES="APPLIES"
    DOES_NOT_APPLY="DOES_NOT_APPLY"
    UNDETERMINED="UNDETERMINED"


class Execution(StrEnum):
    COMPLETED="COMPLETED"
    MISSING_INPUT="MISSING_INPUT"
    UNSUPPORTED_METHOD="UNSUPPORTED_METHOD"
    NUMERICAL_FAILURE="NUMERICAL_FAILURE"
    INTERNAL_ERROR="INTERNAL_ERROR"


class Compliance(StrEnum):
    PASS="PASS"
    FAIL="FAIL"
    NOT_EVALUATED="NOT_EVALUATED"


class Freshness(StrEnum):
    CURRENT="CURRENT"
    STALE="STALE"
    UNKNOWN="UNKNOWN"


@dataclass(frozen=True, slots=True)
class CoverageLedger:
    expected_keys: tuple[str,...]
    completed_keys: tuple[str,...]
    def __post_init__(self):
        if not self.expected_keys or len(self.expected_keys)!=len(set(self.expected_keys)):
            raise ValueError("expected coverage must be nonempty and unique")
        if len(self.completed_keys)!=len(set(self.completed_keys)):
            raise ValueError("duplicate completed key")
        for key in self.expected_keys:
            required(key,"expected coverage key")
        if not set(self.completed_keys).issubset(self.expected_keys):
            raise ValueError("completion outside coverage")
    @property
    def is_complete(self)->bool:
        return set(self.expected_keys)==set(self.completed_keys)


@dataclass(frozen=True, slots=True)
class CheckResult:
    check_id: str
    target_ref: str
    applicability: Applicability
    execution: Execution
    compliance: Compliance
    coverage: CoverageLedger
    freshness: Freshness
    rule: RuleRef
    trace_ref: str | None
    reason: str
    def __post_init__(self):
        required(self.check_id,"check_id")
        required(self.target_ref,"target_ref")
        required(self.reason,"reason")
        if type(self.coverage) is not CoverageLedger or type(self.rule) is not RuleRef:
            raise TypeError("coverage and rule must be typed")
        if self.compliance==Compliance.PASS and (
            self.applicability!=Applicability.APPLIES or
            self.execution!=Execution.COMPLETED or
            not self.coverage.is_complete or
            self.freshness!=Freshness.CURRENT
        ):
            raise ValueError("PASS requires applicable, complete, current result")
        if self.compliance==Compliance.FAIL and (
            self.applicability!=Applicability.APPLIES or
            self.execution!=Execution.COMPLETED or
            not self.coverage.completed_keys
        ):
            raise ValueError("FAIL requires independently completed failing check")
        if self.applicability==Applicability.DOES_NOT_APPLY and self.compliance!=Compliance.NOT_EVALUATED:
            raise ValueError("not applicable is never PASS/FAIL")
        if self.trace_ref is not None:
            required(self.trace_ref,"trace_ref")


@dataclass(frozen=True, slots=True)
class CalculationStep:
    step_id: str
    rule: RuleRef
    inputs: tuple[tuple[str,float,str],...]
    outputs: tuple[tuple[str,float,str],...]
    quality_ref: str
    def __post_init__(self):
        required(self.step_id,"step_id")
        required(self.quality_ref,"quality_ref")
        if type(self.rule) is not RuleRef:
            raise TypeError("typed rule required")
        for name,value,unit in (*self.inputs,*self.outputs):
            required(name,"numeric field")
            required(unit,"numeric unit")
            finite_real(value)
