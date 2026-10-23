"""C1: bounded, explicit first-order signed-demand transformation.

Consumes qualified evidence and a complete *externally declared* source
population. Neither a column code evaluator nor an ETABS accessor; no
second-order, stiffness, load-combo synthesis, or full-column approval.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from math import hypot
from ..domain.coordinates import (
    LocalFrame, ActionVector, AxialSignConvention, transform_action,
    kernel_compression_n,
)
from ..domain.quantities import Force
from ..domain.stations import ResponseKey, StationGeometry
from ..domain.identity import required
from ..domain.member_models import PhysicalColumn, ColumnCandidate, MemberDemandPopulation
from ..domain.analysis_bundle import (
    AnalysisBundle, RequiredRole, EvidenceCatalog,
    ResponseSemantics, QualificationStatus,
)


@dataclass(frozen=True, slots=True)
class StationDemandBinding:
    key: ResponseKey
    source_population_id: str
    geometry: StationGeometry
    target_frame: LocalFrame
    target_frame_ref: str

    def __post_init__(self):
        if type(self.key) is not ResponseKey or type(self.geometry) is not StationGeometry or (
            type(self.target_frame) is not LocalFrame
        ):
            raise TypeError("typed response key, geometry and destination frame required")
        required(self.source_population_id,"source population ID")
        required(self.target_frame_ref,"target frame identity")
        if self.geometry.ref!=self.key.station:
            raise ValueError("station geometry is for another physical response key")
        if self.geometry.local_frame_ref!=self.target_frame_ref:
            raise ValueError("declared station target frame identity mismatch")


@dataclass(frozen=True, slots=True)
class MemberDemandCompileProblem:
    member: PhysicalColumn
    candidate: ColumnCandidate
    population: MemberDemandPopulation
    station_bindings: tuple[StationDemandBinding,...]
    analysis_bundle: AnalysisBundle
    required_role: RequiredRole
    evidence_catalog: EvidenceCatalog
    axial_sign: AxialSignConvention

    def __post_init__(self):
        for name,typ in (
            ("member",PhysicalColumn),("candidate",ColumnCandidate),
            ("population",MemberDemandPopulation),("analysis_bundle",AnalysisBundle),
            ("required_role",RequiredRole),("evidence_catalog",EvidenceCatalog),
            ("axial_sign",AxialSignConvention),
        ):
            if type(getattr(self,name)) is not typ:
                raise TypeError(f"{name} must be {typ.__name__}")
        if type(self.station_bindings) is not tuple or any(
            type(item) is not StationDemandBinding for item in self.station_bindings
        ):
            raise TypeError("immutable typed station population bindings required")
        self.candidate.validate_for(self.member)
        if self.population.member_ref!=self.member.ref:
            raise ValueError("source population for another physical member")
        keys=[b.key for b in self.station_bindings]
        ids=[b.source_population_id for b in self.station_bindings]
        if len(set(keys))!=len(keys) or set(keys)!=set(self.population.expected_keys):
            raise ValueError("exact station binding census required")
        if len(set(ids))!=len(ids) or set(ids)!=set(self.required_role.expected_population):
            raise ValueError("exact source population ID census required")


class DemandCompileStatus(StrEnum):
    READY_FIRST_ORDER_ONLY="READY_FIRST_ORDER_ONLY"
    INCOMPLETE_SOURCE="INCOMPLETE_SOURCE"
    UNQUALIFIED_SOURCE="UNQUALIFIED_SOURCE"
    INVALID_STATION_MAPPING="INVALID_STATION_MAPPING"


@dataclass(frozen=True, slots=True)
class CompiledSignedDemand:
    key: ResponseKey
    source_population_id: str
    source_evidence_id: str
    source_action: ActionVector
    local_action: ActionVector
    n_compression: Force
    destination_frame_ref: str

    def __post_init__(self):
        if any(type(x) is not ActionVector for x in (self.source_action,self.local_action)):
            raise TypeError("typed 6-action record required")
        if type(self.key) is not ResponseKey or type(self.n_compression) is not Force:
            raise TypeError("typed identity and signed axial Force required")
        for s in (self.source_population_id,self.source_evidence_id,self.destination_frame_ref):
            required(s,"compiled source reference")


@dataclass(frozen=True, slots=True)
class CompiledMemberDemandSet:
    member_ref: object
    candidate_ref: object
    status: DemandCompileStatus
    expected_keys: tuple[ResponseKey,...]
    records: tuple[CompiledSignedDemand,...]
    missing_keys: tuple[ResponseKey,...]
    matched_qualification_evidence: tuple[str,...]
    issues: tuple[str,...]
    second_order_status: str = "NOT_EVALUATED"
    full_column_pass: bool = False

    def __post_init__(self):
        if self.full_column_pass:
            raise ValueError("C1 compiler cannot authorize a full-column pass")
        if type(self.status) is not DemandCompileStatus:
            raise TypeError("typed compiler status required")
        if self.second_order_status!="NOT_EVALUATED":
            raise ValueError("second-order effects not evaluated in C1")
        if self.status==DemandCompileStatus.READY_FIRST_ORDER_ONLY and (
            self.missing_keys or self.issues or len(self.records)!=len(self.expected_keys)
        ):
            raise ValueError("READY requires complete qualified first-order population")


def _position_issue(problem: MemberDemandCompileProblem, binding: StationDemandBinding)->str|None:
    """Prove a station is on the physical centreline without using I/J order."""
    member=problem.member
    a=member.bottom.mm
    b=member.top.mm
    p=binding.geometry.position.mm
    d=tuple(y-x for x,y in zip(a,b))
    m=tuple(x-y for x,y in zip(p,a))
    length=member.centreline_length.as_mm
    projection=sum(x*y for x,y in zip(m,d))/length
    perpendicular=hypot(hypot(*(m[i]-projection*d[i]/length for i in (0,1))),
                        m[2]-projection*d[2]/length)
    tol=binding.geometry.matching_tol.as_mm
    if projection < -tol or projection > length+tol or perpendicular>tol:
        return "POSITION_OFF_PHYSICAL_COLUMN"
    if abs(projection-binding.geometry.physical_station.as_mm)>tol:
        return "PHYSICAL_STATION_DISTANCE_MISMATCH"
    offset=hypot(hypot(*(
        x-y for x,y in zip(p[:2],binding.target_frame.origin.mm[:2])
    )),p[2]-binding.target_frame.origin.mm[2])
    if offset>tol:
        return "DESTINATION_FRAME_ORIGIN_MISMATCH"
    s=binding.key.station
    if s.physical_role=="BOTTOM":
        if s.reference_face_id!=member.bottom_face or abs(projection)>tol:
            return "WRONG_BOTTOM_FACE"
    elif s.physical_role=="TOP":
        if s.reference_face_id!=member.top_face or abs(projection-length)>tol:
            return "WRONG_TOP_FACE"
    elif s.physical_role not in (None,"INTERIOR"):
        return "UNKNOWN_PHYSICAL_STATION_ROLE"
    return None


class MemberDemandCompiler:
    @staticmethod
    def compile(problem: MemberDemandCompileProblem) -> CompiledMemberDemandSet:
        if type(problem) is not MemberDemandCompileProblem:
            raise TypeError("typed MemberDemandCompileProblem required")
        pop=problem.population
        def outcome(status,records=(),issues=(),evidence=()):
            return CompiledMemberDemandSet(
                problem.member.ref,problem.candidate.ref,status,pop.expected_keys,
                tuple(records),pop.missing_keys,tuple(evidence),tuple(issues),
            )
        role=problem.required_role
        selected=[b.run for b in problem.analysis_bundle.bindings if b.role==role.role]
        if len(selected)!=1:
            return outcome(DemandCompileStatus.UNQUALIFIED_SOURCE,issues=("SOURCE_ROLE_NOT_UNIQUE",))
        run=selected[0]
        if run.source.response_semantics!=ResponseSemantics.SIGNED_STATIC or (
            ResponseSemantics.SIGNED_STATIC not in role.supported_semantics
        ):
            return outcome(DemandCompileStatus.UNQUALIFIED_SOURCE,issues=("NOT_SIGNED_STATIC_SOURCE",))
        actual_ids={b.source_population_id for b in problem.station_bindings}
        if not actual_ids.issubset(run.population_keys):
            return outcome(DemandCompileStatus.UNQUALIFIED_SOURCE,issues=("RUN_SOURCE_CENSUS_MISMATCH",))
        qualified=problem.analysis_bundle.qualify((role,),problem.evidence_catalog)
        if qualified.status!=QualificationStatus.SCOPE_MATCH:
            return outcome(DemandCompileStatus.UNQUALIFIED_SOURCE,
                           issues=qualified.issues,evidence=qualified.matched_evidence_refs)
        for binding in problem.station_bindings:
            issue=_position_issue(problem,binding)
            if issue is not None:
                return outcome(DemandCompileStatus.INVALID_STATION_MAPPING,
                               issues=(binding.source_population_id+":"+issue,),
                               evidence=qualified.matched_evidence_refs)
        by_key={d.key:d for d in pop.supplied}
        by_binding={b.key:b for b in problem.station_bindings}
        records=[]
        for key in pop.expected_keys:
            supplied=by_key.get(key)
            if supplied is None:
                continue
            station=by_binding[key]
            if key.run_id!=run.run_id or key.result_generation_id!=run.result_generation_id:
                return outcome(DemandCompileStatus.UNQUALIFIED_SOURCE,
                    issues=("RESPONSE_RUN_OR_GENERATION_MISMATCH",),
                    evidence=qualified.matched_evidence_refs)
            if supplied.evidence.source.producer!=run.source.producer or (
                supplied.evidence.source.record_identifier!=station.source_population_id
            ):
                return outcome(DemandCompileStatus.UNQUALIFIED_SOURCE,
                    issues=("SIGNED_ROW_PROVENANCE_MISMATCH",),
                    evidence=qualified.matched_evidence_refs)
            target=transform_action(supplied.action,supplied.source_frame,station.target_frame)
            records.append(CompiledSignedDemand(
                key,station.source_population_id,supplied.evidence.evidence_id,
                supplied.action,target,kernel_compression_n(target,problem.axial_sign),
                station.target_frame_ref,
            ))
        if pop.missing_keys:
            return outcome(DemandCompileStatus.INCOMPLETE_SOURCE,records,
                           ("SOURCE_STATION_POPULATION_INCOMPLETE",),
                           qualified.matched_evidence_refs)
        return outcome(DemandCompileStatus.READY_FIRST_ORDER_ONLY,records,(),
                       qualified.matched_evidence_refs)
