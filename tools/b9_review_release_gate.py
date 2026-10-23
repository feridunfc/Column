"""B9 evidence-only release-gate evaluation. Not an independent Supervisor."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum

from tools.validate_b8_ledger import validate_ledger


class ReviewGate(StrEnum):
    HOLD="HOLD"


@dataclass(frozen=True,slots=True)
class B9ReviewDecision:
    gate: ReviewGate
    open_reasons: tuple[str,...]
    source_anchor: str
    supervisor_independent: bool = False
    def __post_init__(self):
        if self.gate!=ReviewGate.HOLD or self.supervisor_independent:
            raise ValueError("Worker cannot certify independent Supervisor approval")
        if not self.open_reasons:
            raise ValueError("No independent release basis: reasons required")


def evaluate_b9_readiness()->B9ReviewDecision:
    doc=validate_ledger()
    reasons=[]
    if doc["c02_process_status"]!="RATIFIED":
        reasons.append("C02_VERSIONED_PROCESS_CHANGE_NOT_RATIFIED")
    if doc["supervisor_disposition"]!="G0_G1_G2_INDEPENDENT_ACCEPTED":
        reasons.append("INDEPENDENT_SUPERVISOR_GATE_NOT_COMPLETED")
    reasons.extend("CLAUSE_"+row["id"]+"_UNVERIFIED_OR_DEFERRED" for row in doc["constitution_rows"]
                   if row["worker_assessment"] in ("VIOLATION","UNVERIFIED"))
    reasons.extend("TEST_"+row["id"]+"_UNVERIFIED" for row in doc["acceptance_rows"]
                   if row["worker_assessment"] in ("UNVERIFIED","VIOLATION"))
    reasons.extend("OPEN_FINDING_"+item["id"] for item in doc["open_findings"])
    if not reasons:
        reasons.append("INDEPENDENT_ACCEPTANCE_NOT_PROVEN")
    return B9ReviewDecision(ReviewGate.HOLD,tuple(reasons),doc["code_anchor_sha"])


if __name__=="__main__":
    decision=evaluate_b9_readiness()
    print("B9_REVIEW_GATE_HOLD")
    for issue in decision.open_reasons:
        print(" - "+issue)
    print("G0/G1/G2_NOT_INDEPENDENTLY_ACCEPTED; NO_COLUMN_CODE_PASS")
