"""C6 draft public check_column: explicit immutable inputs, single checked flow.

Does not select rebar, call ETABS, mutate scenario, or turn missing
code/second-order evidence into engineering PASS. C-02 not yet ratified.
"""
from __future__ import annotations
from dataclasses import dataclass
from ..domain.scenario import TrialContext
from ..domain.identity import RevisionRef
from ..domain.tolerances import NumericalPolicy
from ..domain.member_models import PhysicalColumn
from ..domain.quantities import Length
from ..domain.outcomes import Compliance
from ..engineering.member_mechanics import (
    MemberGeometryProblem,MemberMechanics,MemberGeometry,
)
from ..engineering.stability import (
    DeclaredEI, StoryScope,DeclaredSecondOrderBasis,MechanicsBasisOutcome,
)
from ..engineering.full_member_demand import (
    FullDemandCompileProblem,MemberDemandOutcome,FullMemberDemandCompiler,
)
from ..engineering.column_evaluator import (
    RequiredColumnCheck, ColumnEvaluationProblem,ColumnEvaluator,
    CandidateResult,CandidateEligibility,
)
from ..domain.identity import EvidenceRef


@dataclass(frozen=True,slots=True)
class CheckRequest:
    trial: TrialContext
    length_problem: MemberGeometryProblem
    stiffness_declarations: tuple[DeclaredEI,...]
    story_scopes: tuple[StoryScope,...]
    effect_bases: tuple[DeclaredSecondOrderBasis,...]
    demand_problem: FullDemandCompileProblem
    required_checks: tuple[RequiredColumnCheck,...]
    numerical_policy: NumericalPolicy
    input_evidence: tuple[EvidenceRef,...]

    def __post_init__(self):
        if type(self.trial) is not TrialContext or type(self.length_problem) is not MemberGeometryProblem:
            raise TypeError("typed scenario/trial and physical length problem required")
        if self.length_problem.trial!=self.trial:
            raise ValueError("geometry/trial mismatch")
        if type(self.demand_problem) is not FullDemandCompileProblem:
            raise TypeError("typed, source-qualified demand population required")
        if self.demand_problem.first_order.candidate.ref!=self.trial.target_candidate.ref:
            raise ValueError("demand candidate is stale")
        for attr,cls in (
            ("stiffness_declarations",DeclaredEI),
            ("story_scopes",StoryScope),
            ("effect_bases",DeclaredSecondOrderBasis),
            ("required_checks",RequiredColumnCheck),
            ("input_evidence",EvidenceRef),
        ):
            vals=getattr(self,attr)
            if type(vals) is not tuple or any(type(x) is not cls for x in vals):
                raise TypeError(attr+" must be immutable typed tuple")
        if not self.required_checks or not self.input_evidence:
            raise ValueError("external mandatory checks and source evidence required")
        if type(self.numerical_policy) is not NumericalPolicy:
            raise TypeError("explicit numerical policy required")


@dataclass(frozen=True,slots=True)
class ColumnResult:
    scenario_ref: RevisionRef
    trial_ref: RevisionRef
    member_ref: RevisionRef
    candidate_ref: RevisionRef
    geometry: MemberGeometry
    mechanics: MechanicsBasisOutcome
    demands: MemberDemandOutcome
    assessment: CandidateResult
    requested_scope: tuple[str,...]
    issues: tuple[str,...]
    outcome: str = "INCOMPLETE_NOT_CODE_APPROVED"
    full_column_design_pass: bool = False

    def __post_init__(self):
        if self.outcome!="INCOMPLETE_NOT_CODE_APPROVED" or self.full_column_design_pass:
            raise ValueError("C6 cannot approve full-column design while open checks exist")
        if self.assessment.eligibility!=CandidateEligibility.UNDETERMINED:
            raise ValueError("candidate eligibility not accepted")
        if tuple(c.check_id for c in self.assessment.checks)!=self.requested_scope:
            raise ValueError("all required scope keys must be represented")
        if any(c.compliance!=Compliance.NOT_EVALUATED for c in self.assessment.checks):
            raise ValueError("C6 cannot invent code compliance")


def check_column(problem:CheckRequest)->ColumnResult:
    """One explicit C2→C3→C4→C5 flow; never claims full suitability."""
    if type(problem) is not CheckRequest:
        raise TypeError("public check_column requires typed CheckRequest")
    trial=problem.trial
    geometry=MemberMechanics.prepare_geometry(problem.length_problem)
    stiffness=MemberMechanics.prepare_stiffness(trial,geometry,problem.stiffness_declarations)
    mechanics=MemberMechanics.resolve(geometry,stiffness,
                                     problem.story_scopes,problem.effect_bases)
    demands=FullMemberDemandCompiler.compile(problem.demand_problem,trial,mechanics)
    evaluation=ColumnEvaluationProblem(
        trial,geometry,mechanics,problem.required_checks,
        problem.numerical_policy,problem.input_evidence,
    )
    assessment=ColumnEvaluator.evaluate(evaluation,trial,demands)
    issues=tuple(dict.fromkeys((*mechanics.issues,*demands.issues,*assessment.issues,
        "FULL_COLUMN_CODE_EVALUATION_NOT_YET_ACCEPTED")))
    return ColumnResult(
        trial.scenario.ref,trial.ref,trial.target_member_ref,trial.target_candidate.ref,
        geometry,mechanics,demands,assessment,
        trial.scenario.required_scope,issues
    )
