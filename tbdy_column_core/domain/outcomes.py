"""Five independent result axes, no automatic design authority."""
from dataclasses import dataclass
from enum import StrEnum


class ApplicabilityStatus(StrEnum):
    APPLIES="APPLIES"
    DOES_NOT_APPLY="DOES_NOT_APPLY"
    UNDETERMINED="UNDETERMINED"


class ExecutionStatus(StrEnum):
    COMPLETED="COMPLETED"
    MISSING_INPUT="MISSING_INPUT"
    UNSUPPORTED_METHOD="UNSUPPORTED_METHOD"
    NUMERICAL_FAILURE="NUMERICAL_FAILURE"
    INTERNAL_ERROR="INTERNAL_ERROR"


class ComplianceStatus(StrEnum):
    PASS="PASS"
    FAIL="FAIL"
    NOT_EVALUATED="NOT_EVALUATED"


class FreshnessStatus(StrEnum):
    CURRENT="CURRENT"
    STALE="STALE"
    UNKNOWN="UNKNOWN"


@dataclass(frozen=True, slots=True)
class CoverageLedger:
    expected_keys: tuple[str, ...]
    completed_keys: tuple[str, ...]
    def __post_init__(self):
        if not self.expected_keys or len(set(self.expected_keys)) != len(self.expected_keys):
            raise ValueError("expected coverage cannot be empty or duplicated")
        if len(set(self.completed_keys)) != len(self.completed_keys):
            raise ValueError("duplicate covered key")
        if not set(self.completed_keys).issubset(set(self.expected_keys)):
            raise ValueError("unexpected coverage item")
    @property
    def is_complete(self):
        return set(self.expected_keys) == set(self.completed_keys)


@dataclass(frozen=True, slots=True)
class CheckResult:
    check_id: str
    applicability: ApplicabilityStatus
    execution: ExecutionStatus
    compliance: ComplianceStatus
    coverage: CoverageLedger
    freshness: FreshnessStatus
    rule_ref: str
    reason: str
    def __post_init__(self):
        if not self.check_id.strip() or not self.reason.strip() or not self.rule_ref.strip():
            raise ValueError("check identity, rule and reason required")
        if self.compliance != ComplianceStatus.NOT_EVALUATED and (
            self.applicability != ApplicabilityStatus.APPLIES or
            self.execution != ExecutionStatus.COMPLETED or
            not self.coverage.is_complete
        ):
            raise ValueError("PASS/FAIL requires applicable, completed, covered check")
        if self.applicability == ApplicabilityStatus.DOES_NOT_APPLY and (
            self.compliance != ComplianceStatus.NOT_EVALUATED
        ):
            raise ValueError("not applicable cannot have compliance PASS")


@dataclass(frozen=True, slots=True)
class CalculationStep:
    rule_ref: str
    input_values: tuple[tuple[str, float, str], ...]
    output_values: tuple[tuple[str, float, str], ...]
    solver_quality: str
    def __post_init__(self):
        if not self.rule_ref or not self.solver_quality:
            raise ValueError("calculation trace requires rule and quality")
