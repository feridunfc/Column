"""C5 candidate evaluation: source-bound observed section numerics, no code PASS.

C-21/C-24: evaluate() consumes explicit MemberDemandOutcome; never calls
the compiler, never searches for a different candidate or invents a
second-order, confinement/shear or connection method. The sample PMM
radial result is a diagnostic only while B9-F02/F03 are unresolved.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import hypot
from ..domain.identity import EvidenceRef,RuleRef,required
from ..domain.outcomes import (
    Applicability,Execution,Compliance,Freshness,CoverageLedger,CheckResult,
)
from ..domain.quantities import Moment
from ..domain.coordinates import AxialSignConvention
from ..domain.tolerances import NumericalPolicy
from ..domain.section_requests import (
    SectionCapacityProblem,FrameModelContract,RadialCapacityAtAxialForce,
    SectionCapacityResult,SectionStatus,
)
from ..domain.scenario import TrialContext
from .member_mechanics import MemberGeometry
from .stability import MechanicsBasisOutcome
from .member_demand import DemandCompileStatus
from .full_member_demand import MemberDemandOutcome, MemberDemandStatus
from .section_solver import SectionSolver


class CandidateEligibility(StrEnum):
    ELIGIBLE="ELIGIBLE"
    REJECTED="REJECTED"
    UNDETERMINED="UNDETERMINED"


@dataclass(frozen=True,slots=True)
class RequiredColumnCheck:
    check_id: str
    rule: RuleRef
    expected_keys: tuple[str,...]
    def __post_init__(self):
        required(self.check_id,"required check")
        if type(self.rule) is not RuleRef or type(self.expected_keys) is not tuple or not self.expected_keys:
            raise ValueError("externally supplied code rule and nonempty coverage required")
        if len(set(self.expected_keys))!=len(self.expected_keys):
            raise ValueError("duplicate required check key")
        for k in self.expected_keys: required(k,"expected coverage key")


@dataclass(frozen=True,slots=True)
class ColumnEvaluationProblem:
    trial: TrialContext
    geometry: MemberGeometry
    mechanics: MechanicsBasisOutcome
    required_checks: tuple[RequiredColumnCheck,...]
    numerical_policy: NumericalPolicy
    input_evidence: tuple[EvidenceRef,...]
    def __post_init__(self):
        if type(self.trial) is not TrialContext or type(self.geometry) is not MemberGeometry or type(self.mechanics) is not MechanicsBasisOutcome:
            raise TypeError("selected trial with matched geometry and mechanics required")
        if type(self.numerical_policy) is not NumericalPolicy:
            raise TypeError("explicit section numeric policy required")
        if type(self.required_checks) is not tuple or any(type(x) is not RequiredColumnCheck for x in self.required_checks):
            raise TypeError("exact required check census required")
        if tuple(c.check_id for c in self.required_checks)!=self.trial.scenario.required_scope:
            raise ValueError("required check scope does not match immutable scenario")
        if type(self.input_evidence) is not tuple or not self.input_evidence or any(type(x) is not EvidenceRef for x in self.input_evidence):
            raise ValueError("source-bound immutable numerical inputs required")
        if self.geometry.trial_ref!=self.trial.ref or self.geometry.candidate_ref!=self.trial.target_candidate.ref:
            raise ValueError("geometry stale for chosen candidate")
        if self.mechanics.geometry!=self.geometry:
            raise ValueError("mechanics not prepared for this geometry")


@dataclass(frozen=True,slots=True)
class PMMObservation:
    source_key: object
    numerical: SectionCapacityResult
    radial_utilization_observed: float | None
    status: str = "SAMPLED_NUMERIC_DIAGNOSTIC_NOT_CODE_ACCEPTANCE"
    def __post_init__(self):
        from ..domain.quantities import finite_real
        if self.radial_utilization_observed is not None and finite_real(self.radial_utilization_observed)<0:
            raise ValueError("observed utilization must be nonnegative")
        if self.status!="SAMPLED_NUMERIC_DIAGNOSTIC_NOT_CODE_ACCEPTANCE":
            raise ValueError("B root/angle acceptance is still pending")


@dataclass(frozen=True,slots=True)
class CandidateResult:
    candidate_ref: object
    member_ref: object
    trial_ref: object
    checks: tuple[CheckResult,...]
    observations: tuple[PMMObservation,...]
    missing_scopes: tuple[str,...]
    issues: tuple[str,...]
    eligibility: CandidateEligibility = CandidateEligibility.UNDETERMINED
    full_column_pass: bool = False
    @property
    def is_complete(self)->bool:
        return not self.missing_scopes and all(
            c.execution==Execution.COMPLETED and c.coverage.is_complete
            and c.compliance in (Compliance.PASS,Compliance.FAIL)
            for c in self.checks)
    @property
    def has_failures(self)->bool:
        return any(c.compliance==Compliance.FAIL for c in self.checks)
    def __post_init__(self):
        if self.eligibility==CandidateEligibility.ELIGIBLE or self.full_column_pass:
            raise ValueError("C5 cannot approve complete candidate while D/E and B acceptance absent")


def _key(k):
    # Stable identity includes shared-station distinct faces/steps.
    return repr(k)


class ColumnEvaluator:
    @staticmethod
    def evaluate(problem:ColumnEvaluationProblem,trial:TrialContext,
                 demands_outcome:MemberDemandOutcome)->CandidateResult:
        if type(problem) is not ColumnEvaluationProblem or type(trial) is not TrialContext or type(demands_outcome) is not MemberDemandOutcome:
            raise TypeError("typed evaluator inputs, no hidden demand compilation")
        if trial!=problem.trial or trial.target_candidate.ref!=demands_outcome.first_order.candidate_ref:
            raise ValueError("evaluator received a different candidate or demand source")
        first=demands_outcome.first_order
        checks=[]
        observations=[]
        issues=list(demands_outcome.issues)
        complete_first=tuple(_key(k) for k in first.expected_keys
                             if k in {x.key for x in first.records})
        frames=dict(demands_outcome.station_frames)
        evidence_ids={x.evidence_id for x in problem.input_evidence}
        if first.status==DemandCompileStatus.READY_FIRST_ORDER_ONLY:
            for row in first.records:
                frame=frames.get(row.key)
                if frame is None or row.source_evidence_id not in evidence_ids:
                    issues.append("PMM_SOURCE_FRAME_OR_EVIDENCE_MISSING")
                    continue
                numeric_problem=SectionCapacityProblem(
                    trial.target_candidate.cage.section,
                    RadialCapacityAtAxialForce(row.n_compression,
                                               row.local_action.m2,row.local_action.m3),
                    problem.numerical_policy,
                    FrameModelContract(frame,AxialSignConvention.F1_COMPRESSION_POSITIVE,
                                       "SECTION_GEOMETRIC_CENTROID"),
                    problem.input_evidence)
                observed=SectionSolver().calculate(numeric_problem)
                utilization=None
                if observed.status==SectionStatus.COMPLETE_RADIAL:
                    utilization=hypot(row.local_action.m2.as_nmm,
                                      row.local_action.m3.as_nmm)/observed.radial_capacity.as_nmm
                    issues.append("SAMPLED_RADIAL_CAPACITY_NOT_CODE_CERTIFIED")
                else:
                    issues.append("PMM_NUMERIC_UNRESOLVED:"+observed.status.value)
                observations.append(PMMObservation(row.key,observed,utilization))
        for check in problem.required_checks:
            expect=check.expected_keys
            completed=()
            if check.check_id=="GEOMETRY":
                # This confirms *source-bound geometry preparation*, not
                # prescriptive member size/spacing or code design.
                completed=tuple(x for x in expect if x=="PHYSICAL_GEOMETRY"
                    and problem.geometry.centreline.as_mm>0)
                execution=Execution.COMPLETED if len(completed)==len(expect) else Execution.MISSING_INPUT
                reason="PHYSICAL_GEOMETRY_PREPARED_NO_CODE_CRITERIA"
            elif check.check_id=="PMM":
                completed=tuple(x for x in expect if x in complete_first)
                execution=(Execution.MISSING_INPUT if not demands_outcome.second_order_approved
                           else Execution.UNSUPPORTED_METHOD)
                reason="B_NUMERIC_ROOT_ANGLE_AND_SECOND_ORDER_METHOD_UNRESOLVED"
            elif check.check_id=="SECOND_ORDER":
                execution=Execution.MISSING_INPUT
                reason="MEMBER_AND_STORY_EFFECTS_NOT_NORMATIVELY_RESOLVED"
            else:
                execution=Execution.UNSUPPORTED_METHOD
                reason="CHECK_METHOD_NOT_IMPLEMENTED_IN_C_STAGE"
            coverage=CoverageLedger(expect,completed)
            checks.append(CheckResult(
                check.check_id,str(trial.target_member_ref.identifier),
                Applicability.APPLIES,execution,Compliance.NOT_EVALUATED,
                coverage,Freshness.UNKNOWN,check.rule,None,reason
            ))
            if execution!=Execution.COMPLETED or not coverage.is_complete:
                issues.append(check.check_id+":"+reason)
        missing=tuple(c.check_id for c in checks if
                      c.execution!=Execution.COMPLETED or
                      c.compliance==Compliance.NOT_EVALUATED or
                      not c.coverage.is_complete)
        return CandidateResult(
            trial.target_candidate.ref,trial.target_member_ref,trial.ref,
            tuple(checks),tuple(observations),missing,tuple(dict.fromkeys(issues))
        )
