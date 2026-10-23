"""C4: immutable first-order + explicitly *unapproved* second-order branches.

Every response has a source parent key and an externally declared expected
branch identity. No spectral-envelope mixing; no additive/amplified numeric
interpretation without a separately accepted rule/method/stability basis.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from ..domain.identity import EvidenceRef,RuleRef,required
from ..domain.stations import ResponseKey,StepKind
from ..domain.coordinates import ActionVector,LocalFrame,transform_action
from ..domain.scenario import TrialContext
from .member_demand import (
    MemberDemandCompileProblem, MemberDemandCompiler,
    CompiledMemberDemandSet, DemandCompileStatus,
)
from .stability import MechanicsBasisOutcome,EffectScale,BendingAxis


@dataclass(frozen=True,slots=True)
class EffectBranchKey:
    parent: ResponseKey
    scale: EffectScale
    direction: BendingAxis
    method: RuleRef
    def __post_init__(self):
        if type(self.parent) is not ResponseKey or type(self.scale) is not EffectScale or type(self.direction) is not BendingAxis or type(self.method) is not RuleRef:
            raise TypeError("parent response, scale, direction and method required")


@dataclass(frozen=True,slots=True)
class SourceEffectAction:
    key: EffectBranchKey
    action: ActionVector
    source_frame: LocalFrame
    source_run_id: str
    result_generation_id: str
    evidence: EvidenceRef
    def __post_init__(self):
        if type(self.key) is not EffectBranchKey or type(self.action) is not ActionVector or type(self.source_frame) is not LocalFrame or type(self.evidence) is not EvidenceRef:
            raise TypeError("typed source effect action required")
        required(self.source_run_id,"source run")
        required(self.result_generation_id,"source generation")
        if self.key.parent.step.kind in (StepKind.ENVELOPE_MAX,StepKind.ENVELOPE_MIN,StepKind.MODE):
            raise ValueError("non-concurrent source step cannot be fabricated as signed effect")


@dataclass(frozen=True,slots=True)
class FullDemandCompileProblem:
    first_order: MemberDemandCompileProblem
    expected_effect_branches: tuple[EffectBranchKey,...]
    supplied_effects: tuple[SourceEffectAction,...]
    def __post_init__(self):
        if type(self.first_order) is not MemberDemandCompileProblem:
            raise TypeError("C1 first order problem required")
        if type(self.expected_effect_branches) is not tuple or type(self.supplied_effects) is not tuple:
            raise TypeError("immutable external effect census required")
        if any(type(x) is not EffectBranchKey for x in self.expected_effect_branches) or any(type(x) is not SourceEffectAction for x in self.supplied_effects):
            raise TypeError("typed second-order branch population required")
        expected=set(self.expected_effect_branches)
        supplied=[x.key for x in self.supplied_effects]
        if not expected or len(expected)!=len(self.expected_effect_branches) or len(set(supplied))!=len(supplied):
            raise ValueError("nonempty unique externally declared second-order census required")
        if not set(supplied).issubset(expected) or not {k.parent for k in expected}.issubset(self.first_order.population.expected_keys):
            raise ValueError("effect has no declared parent response or branch")


@dataclass(frozen=True,slots=True)
class TransformedEffect:
    key: EffectBranchKey
    local_action: ActionVector
    source_evidence_id: str
    qualification: str = "UNVERIFIED_EFFECT_MODEL"
    def __post_init__(self):
        if self.qualification!="UNVERIFIED_EFFECT_MODEL":
            raise ValueError("source-declared branch cannot claim validated second-order method")


class MemberDemandStatus(StrEnum):
    FIRST_ORDER_ONLY="FIRST_ORDER_ONLY"
    FIRST_ORDER_PARTIAL="FIRST_ORDER_PARTIAL"
    SOURCE_UNQUALIFIED="SOURCE_UNQUALIFIED"


@dataclass(frozen=True,slots=True)
class MemberDemandOutcome:
    first_order: CompiledMemberDemandSet
    effects: tuple[TransformedEffect,...]
    expected_effect_branches: tuple[EffectBranchKey,...]
    missing_effect_branches: tuple[EffectBranchKey,...]
    issues: tuple[str,...]
    status: MemberDemandStatus
    second_order_approved: bool = False
    full_column_pass: bool = False
    station_frames: tuple[tuple[ResponseKey,LocalFrame], ...] = ()
    def __post_init__(self):
        if type(self.station_frames) is not tuple or any(
                type(row) is not tuple or len(row)!=2 or
                type(row[0]) is not ResponseKey or type(row[1]) is not LocalFrame
                for row in self.station_frames):
            raise TypeError("immutable typed response-specific frames required")
        if len({x[0] for x in self.station_frames})!=len(self.station_frames):
            raise ValueError("duplicate target frame mapping")
        if self.second_order_approved or self.full_column_pass:
            raise ValueError("C4 must not claim amplified code-approved actions")
        if type(self.status) is not MemberDemandStatus:
            raise TypeError("typed status required")


class FullMemberDemandCompiler:
    @staticmethod
    def compile(problem:FullDemandCompileProblem,trial:TrialContext,
                mechanics_outcome:MechanicsBasisOutcome)->MemberDemandOutcome:
        if type(problem) is not FullDemandCompileProblem or type(trial) is not TrialContext or type(mechanics_outcome) is not MechanicsBasisOutcome:
            raise TypeError("typed C4 problem, selected trial and mechanics dependency census required")
        first=problem.first_order
        if first.member.ref!=trial.target_member_ref or first.candidate.ref!=trial.target_candidate.ref:
            raise ValueError("source demands not bound to selected trial candidate")
        if mechanics_outcome.geometry.trial_ref!=trial.ref or mechanics_outcome.geometry.candidate_ref!=trial.target_candidate.ref:
            raise ValueError("mechanics source tied to stale trial/candidate")
        raw=MemberDemandCompiler.compile(first)
        issues=list(raw.issues)
        frame_by_key={b.key:b.target_frame for b in first.station_bindings}
        run_by_role={b.role:b.run for b in first.analysis_bundle.bindings}
        expected=set(problem.expected_effect_branches)
        available=[]
        # Only retain matching, explicitly sourced branches. Do NOT
        # sum raw+global+local here or replace first order by envelopes.
        for effect in problem.supplied_effects:
            k=effect.key
            run=run_by_role.get(first.required_role.role)
            if run is None or effect.source_run_id!=run.run_id or effect.result_generation_id!=run.result_generation_id:
                issues.append("EFFECT_RUN_OR_GENERATION_UNQUALIFIED")
                continue
            if effect.evidence.source.producer!=run.source.producer:
                issues.append("EFFECT_PRODUCER_UNQUALIFIED")
                continue
            if not any(b.scale==k.scale and b.axis==k.direction and b.method==k.method
                       and b.run_id==effect.source_run_id and b.source_result_generation==effect.result_generation_id
                       for b in mechanics_outcome.effects):
                issues.append("EFFECT_METHOD_OR_SOURCE_BASIS_UNQUALIFIED")
                continue
            frame=frame_by_key.get(k.parent)
            if frame is None:
                issues.append("EFFECT_PARENT_STATION_UNRESOLVED")
                continue
            transformed=transform_action(effect.action,effect.source_frame,frame)
            available.append(TransformedEffect(k,transformed,effect.evidence.evidence_id))
        supplied_keys={x.key for x in available}
        missing=tuple(k for k in problem.expected_effect_branches if k not in supplied_keys)
        if missing: issues.append("EXPECTED_SECOND_ORDER_BRANCHES_MISSING")
        issues.extend(mechanics_outcome.issues)
        issues.append("SECOND_ORDER_NUMERICAL_APPLICATION_AND_METHOD_NOT_ACCEPTED")
        status=(MemberDemandStatus.SOURCE_UNQUALIFIED if raw.status in
                (DemandCompileStatus.UNQUALIFIED_SOURCE,DemandCompileStatus.INVALID_STATION_MAPPING)
                else MemberDemandStatus.FIRST_ORDER_PARTIAL if raw.status==DemandCompileStatus.INCOMPLETE_SOURCE
                else MemberDemandStatus.FIRST_ORDER_ONLY)
        return MemberDemandOutcome(raw,tuple(available),tuple(problem.expected_effect_branches),
                                   missing,tuple(dict.fromkeys(issues)),status,
                                   station_frames=tuple((x.key,x.target_frame)
                                                        for x in first.station_bindings))
