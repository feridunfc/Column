"""C3: source-bound EI facts and member/story second-order dependency census.

All records here are *declared*, not verified structural stiffness or a
numerical P-Delta/P-delta result. No unilateral EI reduction, K factor,
global sway method, nominal curvature, or design PASS.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from ..domain.identity import RevisionRef, EvidenceRef, RuleRef, required
from ..domain.quantities import finite_real
from ..engineering.member_mechanics import MemberGeometry
from ..domain.scenario import TrialContext


class BendingAxis(StrEnum):
    LOCAL_2="LOCAL_2"
    LOCAL_3="LOCAL_3"


class EffectScale(StrEnum):
    GLOBAL_P_DELTA="GLOBAL_P_DELTA"
    LOCAL_P_DELTA="LOCAL_P_DELTA"


@dataclass(frozen=True,slots=True)
class DeclaredEI:
    axis: BendingAxis
    ei_nmm2: float
    model_rule: RuleRef
    evidence: EvidenceRef
    member_ref: RevisionRef
    candidate_ref: RevisionRef
    def __post_init__(self):
        if type(self.axis) is not BendingAxis or type(self.model_rule) is not RuleRef:
            raise TypeError("explicit axis and EI model rule required")
        if any(type(x) is not RevisionRef for x in (self.member_ref,self.candidate_ref)) or type(self.evidence) is not EvidenceRef:
            raise TypeError("revisioned EI source, member and candidate required")
        if finite_real(self.ei_nmm2)<=0:
            raise ValueError("source-declared flexural rigidity must be positive")


@dataclass(frozen=True,slots=True)
class StiffnessCensus:
    geometry: MemberGeometry
    declarations: tuple[DeclaredEI,...]
    missing_axes: tuple[BendingAxis,...]
    state: str = "DECLARED_EI_NOT_NORMATIVELY_QUALIFIED"
    def __post_init__(self):
        if type(self.geometry) is not MemberGeometry or type(self.declarations) is not tuple:
            raise TypeError("source geometry and immutable EI census required")
        if self.state!="DECLARED_EI_NOT_NORMATIVELY_QUALIFIED":
            raise ValueError("C3 cannot assert qualified EI")


@dataclass(frozen=True,slots=True)
class StoryScope:
    direction: BendingAxis
    run_id: str
    expected_member_refs: tuple[RevisionRef,...]
    supplied_member_refs: tuple[RevisionRef,...]
    evidence: EvidenceRef
    method: RuleRef
    def __post_init__(self):
        required(self.run_id,"story run")
        if type(self.direction) is not BendingAxis or type(self.evidence) is not EvidenceRef or type(self.method) is not RuleRef:
            raise TypeError("source-bound story direction/method required")
        for a in (self.expected_member_refs,self.supplied_member_refs):
            if type(a) is not tuple or any(type(x) is not RevisionRef for x in a) or len(set(a))!=len(a):
                raise ValueError("unique typed expected/supplied story member census required")
        if not self.expected_member_refs or not set(self.supplied_member_refs).issubset(self.expected_member_refs):
            raise ValueError("story scope cannot be synthesized from target column")


@dataclass(frozen=True,slots=True)
class DeclaredSecondOrderBasis:
    scale: EffectScale
    axis: BendingAxis
    run_id: str
    method: RuleRef
    evidence: EvidenceRef
    source_result_generation: str
    def __post_init__(self):
        if type(self.scale) is not EffectScale or type(self.axis) is not BendingAxis or type(self.method) is not RuleRef or type(self.evidence) is not EvidenceRef:
            raise TypeError("explicit second-order effect kind, direction, source and method required")
        required(self.run_id,"source run")
        required(self.source_result_generation,"result generation")


@dataclass(frozen=True,slots=True)
class MechanicsBasisOutcome:
    geometry: MemberGeometry
    stiffness: StiffnessCensus
    story: tuple[StoryScope,...]
    effects: tuple[DeclaredSecondOrderBasis,...]
    missing_effects: tuple[tuple[EffectScale,BendingAxis],...]
    issues: tuple[str,...]
    status: str = "DEPENDENCY_DECLARED_UNRESOLVED"
    second_order_computed: bool = False
    def __post_init__(self):
        if self.status!="DEPENDENCY_DECLARED_UNRESOLVED" or self.second_order_computed:
            raise ValueError("C3 does not calculate or approve second-order actions")


class StabilityCensus:
    @staticmethod
    def prepare_stiffness(trial:TrialContext,geometry:MemberGeometry,
                          declarations:tuple[DeclaredEI,...])->StiffnessCensus:
        if type(trial) is not TrialContext or type(geometry) is not MemberGeometry:
            raise TypeError("trial and physically prepared geometry required")
        if geometry.trial_ref!=trial.ref or geometry.candidate_ref!=trial.target_candidate.ref:
            raise ValueError("stiffness declaration on stale candidate/trial geometry")
        if type(declarations) is not tuple or any(type(x) is not DeclaredEI for x in declarations):
            raise TypeError("immutable typed EI population required")
        axes=[x.axis for x in declarations]
        if len(axes)!=len(set(axes)):
            raise ValueError("duplicate EI axis")
        if any(x.member_ref!=geometry.member_ref or x.candidate_ref!=geometry.candidate_ref for x in declarations):
            raise ValueError("EI member/candidate revision mismatch")
        return StiffnessCensus(geometry,declarations,tuple(a for a in BendingAxis if a not in axes))

    @staticmethod
    def resolve(geometry:MemberGeometry,stiffness:StiffnessCensus,
                story:tuple[StoryScope,...],basis:tuple[DeclaredSecondOrderBasis,...]
                )->MechanicsBasisOutcome:
        if type(geometry) is not MemberGeometry or type(stiffness) is not StiffnessCensus or stiffness.geometry!=geometry:
            raise TypeError("matching source geometry and EI required")
        if any(type(x) is not StoryScope for x in story) or type(story) is not tuple:
            raise TypeError("typed immutable story scope required")
        if type(basis) is not tuple or any(type(x) is not DeclaredSecondOrderBasis for x in basis):
            raise TypeError("typed immutable second-order basis required")
        issue=[]
        bydir={s.direction:s for s in story}
        if len(bydir)!=len(story):
            raise ValueError("duplicate story direction")
        for direction in BendingAxis:
            s=bydir.get(direction)
            if s is None:
                issue.append(direction.value+":STORY_SCOPE_MISSING")
            elif geometry.member_ref not in s.expected_member_refs or (
                set(s.expected_member_refs)!=set(s.supplied_member_refs)
            ):
                issue.append(direction.value+":STORY_POPULATION_INCOMPLETE")
        ids=[(e.scale,e.axis) for e in basis]
        if len(ids)!=len(set(ids)):
            raise ValueError("duplicate second-order scale/axis")
        missing=tuple((scale,axis) for scale in EffectScale for axis in BendingAxis
                      if (scale,axis) not in ids)
        if missing:
            issue.append("SECOND_ORDER_BASIS_INCOMPLETE")
        if stiffness.missing_axes:
            issue.append("EI_AXIS_INCOMPLETE")
        for effect in basis:
            match=bydir.get(effect.axis)
            if match is None or match.run_id!=effect.run_id:
                issue.append(effect.axis.value+":EFFECT_STORY_RUN_MISMATCH")
        issue.append("DECLARED_EI_AND_EFFECTS_REQUIRE_METHOD_QUALIFICATION")
        return MechanicsBasisOutcome(geometry,stiffness,story,basis,missing,tuple(issue))
