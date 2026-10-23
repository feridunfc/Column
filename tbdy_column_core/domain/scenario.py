"""C2 provisional immutable DesignScenario and single-target TrialContext.

C-05/C-07/C-16/C-22: no ETABS, design search, full-column check, or
tacit rewrite of model/neighbor assignments. C-02 scope amendment pending.
"""
from __future__ import annotations

from dataclasses import dataclass
from .identity import RevisionRef, required
from .member_models import PhysicalColumn, ColumnCandidate
from .analysis_bundle import AnalysisBundle


@dataclass(frozen=True, slots=True)
class DesignScenario:
    ref: RevisionRef
    model_ref: RevisionRef
    basis_ref: RevisionRef
    analysis_bundle: AnalysisBundle
    members: tuple[PhysicalColumn, ...]
    assignments: tuple[ColumnCandidate, ...]
    required_scope: tuple[str, ...]

    def __post_init__(self):
        for name in ("ref", "model_ref", "basis_ref"):
            if type(getattr(self, name)) is not RevisionRef:
                raise TypeError(f"{name} requires RevisionRef")
        if type(self.analysis_bundle) is not AnalysisBundle:
            raise TypeError("explicit AnalysisBundle required")
        if type(self.members) is not tuple or not self.members or any(
                type(m) is not PhysicalColumn for m in self.members):
            raise TypeError("nonempty immutable physical member census required")
        if type(self.assignments) is not tuple or any(
                type(a) is not ColumnCandidate for a in self.assignments):
            raise TypeError("immutable candidate assignment census required")
        if type(self.required_scope) is not tuple or not self.required_scope or any(
                not isinstance(k, str) for k in self.required_scope):
            raise ValueError("externally declared nonempty required scope")
        for key in self.required_scope:
            required(key, "required scope key")
        if len(set(self.required_scope))!=len(self.required_scope):
            raise ValueError("duplicated required scope identity")
        members={m.ref:m for m in self.members}
        if len(members)!=len(self.members):
            raise ValueError("duplicated physical member revisions")
        if len({(m.ref.namespace,m.ref.identifier) for m in self.members})!=len(self.members):
            raise ValueError("multiple current revisions for one physical member")
        ids=[a.member_ref for a in self.assignments]
        if len(ids)!=len(set(ids)):
            raise ValueError("duplicated candidate assignment for one member")
        if set(ids)!=set(members):
            raise ValueError("a physical member must have exactly one supplied candidate")
        for candidate in self.assignments:
            candidate.validate_for(members[candidate.member_ref])

    def member_for(self, ref:RevisionRef)->PhysicalColumn:
        if type(ref) is not RevisionRef:
            raise TypeError("member revision required")
        found=[m for m in self.members if m.ref==ref]
        if len(found)!=1:
            raise ValueError("member revision not in scenario")
        return found[0]

    def candidate_for(self, ref:RevisionRef)->ColumnCandidate:
        self.member_for(ref)
        matches=[a for a in self.assignments if a.member_ref==ref]
        if len(matches)!=1:
            raise ValueError("candidate not uniquely assigned to member")
        return matches[0]


@dataclass(frozen=True,slots=True)
class TrialContext:
    ref: RevisionRef
    scenario: DesignScenario
    target_member_ref: RevisionRef
    target_candidate: ColumnCandidate

    def __post_init__(self):
        if type(self.ref) is not RevisionRef or type(self.scenario) is not DesignScenario:
            raise TypeError("revisioned trial and immutable scenario required")
        if type(self.target_member_ref) is not RevisionRef or type(self.target_candidate) is not ColumnCandidate:
            raise TypeError("revisioned selected target/candidate required")
        member=self.scenario.member_for(self.target_member_ref)
        original=self.scenario.candidate_for(self.target_member_ref)
        self.target_candidate.validate_for(member)
        if (self.target_candidate.ref.namespace,self.target_candidate.ref.identifier)!=(
                original.ref.namespace,original.ref.identifier):
            raise ValueError("selected trial candidate must preserve baseline candidate identity")

    @property
    def selected_member(self)->PhysicalColumn:
        return self.scenario.member_for(self.target_member_ref)

    def resolve_candidate(self, member_ref:RevisionRef)->ColumnCandidate:
        if type(member_ref) is not RevisionRef:
            raise TypeError("revisioned member reference required")
        if member_ref==self.target_member_ref:
            return self.target_candidate
        return self.scenario.candidate_for(member_ref)
