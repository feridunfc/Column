"""C2 physical geometry preparation, with explicit and distinct length facts.

No auto-filled net/unsupported/effective lengths. Declared LengthEvidence
is not verification by itself: second-order calculation is strictly blocked
until the source qualification and method basis are implemented in C3.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from ..domain.identity import RevisionRef, EvidenceRef, RuleRef
from ..domain.coordinates import Point3D
from ..domain.quantities import Length
from ..domain.scenario import TrialContext


class LengthKind(StrEnum):
    CLEAR="CLEAR_LENGTH"
    UNBRACED_LOCAL_2="UNBRACED_LOCAL_2"
    UNBRACED_LOCAL_3="UNBRACED_LOCAL_3"
    EFFECTIVE_LOCAL_2="EFFECTIVE_LOCAL_2"
    EFFECTIVE_LOCAL_3="EFFECTIVE_LOCAL_3"


@dataclass(frozen=True, slots=True)
class DeclaredLength:
    kind: LengthKind
    value: Length
    evidence: EvidenceRef
    method: RuleRef | None = None

    def __post_init__(self):
        if type(self.kind) is not LengthKind or type(self.value) is not Length:
            raise TypeError("typed distinct length kind and physical Length required")
        if self.value.as_mm<=0:
            raise ValueError("declared length must be positive")
        if type(self.evidence) is not EvidenceRef:
            raise TypeError("source-bound evidence required, never inferred from storey height")
        if self.method is not None and type(self.method) is not RuleRef:
            raise TypeError("length method must carry RuleRef")
        if self.kind in (LengthKind.EFFECTIVE_LOCAL_2, LengthKind.EFFECTIVE_LOCAL_3):
            if self.method is None:
                raise ValueError("effective length needs an explicit declared method identity")


@dataclass(frozen=True, slots=True)
class MemberGeometryProblem:
    trial: TrialContext
    member_ref: RevisionRef
    supplied_lengths: tuple[DeclaredLength, ...]

    def __post_init__(self):
        if type(self.trial) is not TrialContext or type(self.member_ref) is not RevisionRef:
            raise TypeError("trial and member revision required")
        if self.member_ref!=self.trial.target_member_ref:
            raise ValueError("geometry problem cannot silently target neighbor member")
        if type(self.supplied_lengths) is not tuple or any(
                type(v) is not DeclaredLength for v in self.supplied_lengths):
            raise TypeError("explicit immutable declared-length census required")
        kinds=[v.kind for v in self.supplied_lengths]
        if len(set(kinds))!=len(kinds):
            raise ValueError("conflicting supplied lengths of the same kind")


@dataclass(frozen=True, slots=True)
class MemberGeometry:
    member_ref: RevisionRef
    candidate_ref: RevisionRef
    scenario_ref: RevisionRef
    trial_ref: RevisionRef
    bottom: Point3D
    top: Point3D
    bottom_face_id: str
    top_face_id: str
    centreline: Length
    supplied_lengths: tuple[DeclaredLength, ...]
    missing_length_kinds: tuple[LengthKind, ...]
    status: str = "PHYSICAL_GEOMETRY_DECLARED_ONLY"
    stiffness_ready: bool = False
    second_order_ready: bool = False

    def __post_init__(self):
        if type(self.centreline) is not Length or self.centreline.as_mm<=0:
            raise ValueError("physical centreline required")
        if self.stiffness_ready or self.second_order_ready:
            raise ValueError("C2 cannot self-qualify stiffness or second-order effects")
        if self.status!="PHYSICAL_GEOMETRY_DECLARED_ONLY":
            raise ValueError("C2 has only declared-source physical geometry")


class MemberMechanics:
    @staticmethod
    def prepare_geometry(problem:MemberGeometryProblem)->MemberGeometry:
        if type(problem) is not MemberGeometryProblem:
            raise TypeError("typed MemberGeometryProblem required")
        trial=problem.trial
        member=trial.selected_member
        chosen=trial.resolve_candidate(problem.member_ref)
        chosen.validate_for(member)
        length=member.centreline_length
        facts={v.kind:v for v in problem.supplied_lengths}
        if LengthKind.CLEAR in facts and facts[LengthKind.CLEAR].value.as_mm>length.as_mm:
            raise ValueError("physical clear length cannot exceed centreline under declared C2 geometry")
        missing=tuple(k for k in LengthKind if k not in facts)
        return MemberGeometry(
            member.ref,chosen.ref,trial.scenario.ref,trial.ref,member.bottom,member.top,
            member.bottom_face,member.top_face,length,problem.supplied_lengths,missing
        )

    @staticmethod
    def prepare_stiffness(trial,geometry,declarations):
        from .stability import StabilityCensus
        return StabilityCensus.prepare_stiffness(trial,geometry,declarations)

    @staticmethod
    def resolve(geometry,stiffness,story,basis):
        from .stability import StabilityCensus
        return StabilityCensus.resolve(geometry,stiffness,story,basis)
