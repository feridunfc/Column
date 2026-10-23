"""C0: immutable physical-column, selected cage and signed response census.

Domain facts only: neither code compliance nor a check_column implementation.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from enum import StrEnum
from math import hypot
from .identity import RevisionRef, EvidenceRef, required
from .quantities import Length
from .coordinates import Point3D, ActionVector, LocalFrame
from .section_models import RCSection
from .stations import ResponseKey, StepKind


class PhysicalEnd(StrEnum):
    BOTTOM="PHYSICAL_BOTTOM"
    TOP="PHYSICAL_TOP"


@dataclass(frozen=True, slots=True)
class PhysicalColumn:
    ref: RevisionRef
    section_ref: RevisionRef
    bottom: Point3D
    top: Point3D
    bottom_face: str
    top_face: str

    def __post_init__(self):
        if type(self.ref) is not RevisionRef or type(self.section_ref) is not RevisionRef:
            raise TypeError("revisioned physical member and section references required")
        if type(self.bottom) is not Point3D or type(self.top) is not Point3D:
            raise TypeError("physical end coordinates required")
        required(self.bottom_face,"bottom face")
        required(self.top_face,"top face")
        if self.top.z.as_mm<=self.bottom.z.as_mm:
            raise ValueError("top must be vertically above physical bottom")

    @property
    def centreline_length(self)->Length:
        a,b=self.bottom.mm,self.top.mm
        return Length.mm(hypot(hypot(b[0]-a[0],b[1]-a[1]),b[2]-a[2]))

    def face(self,end:PhysicalEnd)->str:
        if type(end) is not PhysicalEnd:
            raise TypeError("explicit physical end required")
        return self.bottom_face if end==PhysicalEnd.BOTTOM else self.top_face


@dataclass(frozen=True, slots=True)
class RectangularTie:
    tie_id: str
    diameter: Length
    x2_min: Length
    x2_max: Length
    x3_min: Length
    x3_max: Length

    def __post_init__(self):
        required(self.tie_id,"tie identity")
        for v in (self.diameter,self.x2_min,self.x2_max,self.x3_min,self.x3_max):
            if type(v) is not Length:
                raise TypeError("typed tie geometry lengths required")
        if not (self.diameter.as_mm>0 and self.x2_min.as_mm<self.x2_max.as_mm and
                self.x3_min.as_mm<self.x3_max.as_mm):
            raise ValueError("nondegenerate actual tie geometry required")

    def validate_section(self,section:RCSection)->None:
        if type(section) is not RCSection:
            raise TypeError("RCSection required")
        if self.diameter!=section.longitudinal.tie_diameter:
            raise ValueError("tie diameter mismatches longitudinal declared tie")
        clearance=section.longitudinal.clear_cover.as_mm+self.diameter.as_mm/2
        if max(abs(self.x2_min.as_mm),abs(self.x2_max.as_mm))+clearance>section.profile.b.as_mm/2 or (
            max(abs(self.x3_min.as_mm),abs(self.x3_max.as_mm))+clearance>section.profile.h.as_mm/2):
            raise ValueError("tie violates concrete outer cover")


@dataclass(frozen=True, slots=True)
class Crosstie:
    crosstie_id: str
    first_bar_id: str
    second_bar_id: str
    diameter: Length

    def __post_init__(self):
        for name in ("crosstie_id","first_bar_id","second_bar_id"):
            required(getattr(self,name),name)
        if self.first_bar_id==self.second_bar_id:
            raise ValueError("crosstie needs two different physical bars")
        if type(self.diameter) is not Length or self.diameter.as_mm<=0:
            raise ValueError("positive crosstie diameter required")


@dataclass(frozen=True, slots=True)
class TransverseRegion:
    region_id: str
    start: Length
    finish: Length
    spacing: Length
    tie_id: str
    crosstie_ids: tuple[str,...]

    def __post_init__(self):
        required(self.region_id,"region ID")
        required(self.tie_id,"tie ID")
        if any(type(x) is not Length for x in (self.start,self.finish,self.spacing)):
            raise TypeError("region limits/spacing must be typed Length")
        if not (0<=self.start.as_mm<self.finish.as_mm and self.spacing.as_mm>0):
            raise ValueError("positive complete region geometry required")
        if type(self.crosstie_ids) is not tuple or len(set(self.crosstie_ids))!=len(self.crosstie_ids):
            raise ValueError("unique immutable crosstie IDs required")


@dataclass(frozen=True, slots=True)
class RebarCage:
    ref: RevisionRef
    section: RCSection
    ties: tuple[RectangularTie,...]
    crossties: tuple[Crosstie,...]
    regions: tuple[TransverseRegion,...]

    def __post_init__(self):
        if type(self.ref) is not RevisionRef or type(self.section) is not RCSection:
            raise TypeError("physical cage and source section required")
        for values,typ in ((self.ties,RectangularTie),(self.crossties,Crosstie),(self.regions,TransverseRegion)):
            if type(values) is not tuple or any(type(x) is not typ for x in values):
                raise TypeError("typed immutable transverse census required")
        if not self.ties or not self.regions:
            raise ValueError("full cage requires supplied ties and regions")
        tieids=[x.tie_id for x in self.ties]
        crossids=[x.crosstie_id for x in self.crossties]
        regionids=[x.region_id for x in self.regions]
        if any(len(x)!=len(set(x)) for x in (tieids,crossids,regionids)):
            raise ValueError("duplicate transverse identity")
        bars={b.bar_id for b in self.section.longitudinal.bars}
        for t in self.ties:
            t.validate_section(self.section)
        for c in self.crossties:
            if c.first_bar_id not in bars or c.second_bar_id not in bars:
                raise ValueError("crosstie references unsupplied physical longitudinal bars")
        ordered=sorted(self.regions,key=lambda x:x.start.as_mm)
        if ordered[0].start.as_mm!=0:
            raise ValueError("region census must begin at physical bottom")
        for a,b in zip(ordered,ordered[1:]):
            if a.finish.as_mm!=b.start.as_mm:
                raise ValueError("transverse census gap or overlap")
        for reg in ordered:
            if reg.tie_id not in tieids or not set(reg.crosstie_ids).issubset(crossids):
                raise ValueError("unresolved region tie/crosstie")

    def validate_for(self,member:PhysicalColumn)->None:
        if type(member) is not PhysicalColumn:
            raise TypeError("physical member required")
        if self.section.ref!=member.section_ref:
            raise ValueError("member's source section revision changed")
        if abs(max(r.finish.as_mm for r in self.regions)-member.centreline_length.as_mm)>1e-6:
            raise ValueError("transverse region population not complete")


@dataclass(frozen=True, slots=True)
class ColumnCandidate:
    ref: RevisionRef
    member_ref: RevisionRef
    cage: RebarCage

    def __post_init__(self):
        if type(self.ref) is not RevisionRef or type(self.member_ref) is not RevisionRef or type(self.cage) is not RebarCage:
            raise TypeError("candidate must bind member revision and actual cage")

    def validate_for(self,member:PhysicalColumn)->None:
        if type(member) is not PhysicalColumn or member.ref!=self.member_ref:
            raise ValueError("candidate-member identity/revision mismatch")
        self.cage.validate_for(member)

    def with_cage(self,new_cage:RebarCage,new_ref:RevisionRef)->ColumnCandidate:
        if type(new_cage) is not RebarCage or type(new_ref) is not RevisionRef:
            raise TypeError("typed immutable amendment required")
        if (new_ref.namespace,new_ref.identifier)!=(self.ref.namespace,self.ref.identifier) or new_ref.revision==self.ref.revision:
            raise ValueError("new cage must create new revision of same candidate")
        return replace(self,ref=new_ref,cage=new_cage)


@dataclass(frozen=True, slots=True)
class SignedMemberDemand:
    key: ResponseKey
    action: ActionVector
    source_frame: LocalFrame
    evidence: EvidenceRef

    def __post_init__(self):
        if type(self.key) is not ResponseKey or type(self.action) is not ActionVector or type(self.source_frame) is not LocalFrame or type(self.evidence) is not EvidenceRef:
            raise TypeError("source-bound signed six-vector required")
        if self.key.step.kind in (StepKind.ENVELOPE_MAX,StepKind.ENVELOPE_MIN):
            raise ValueError("envelope maximum cannot be treated as a concurrent signed six-vector")


@dataclass(frozen=True, slots=True)
class MemberDemandPopulation:
    member_ref: RevisionRef
    expected_keys: tuple[ResponseKey,...]
    supplied: tuple[SignedMemberDemand,...]

    def __post_init__(self):
        if type(self.member_ref) is not RevisionRef:
            raise TypeError("physical member reference required")
        if type(self.expected_keys) is not tuple or not self.expected_keys or any(type(x) is not ResponseKey for x in self.expected_keys):
            raise TypeError("externally declared expected population required")
        if type(self.supplied) is not tuple or any(type(x) is not SignedMemberDemand for x in self.supplied):
            raise TypeError("supplied demands must be immutable typed records")
        keys=[d.key for d in self.supplied]
        if len(set(keys))!=len(keys) or not set(keys).issubset(self.expected_keys) or len(set(self.expected_keys))!=len(self.expected_keys):
            raise ValueError("duplicate or unrequested response key")
        if any(k.station.physical_member_id!=self.member_ref.identifier for k in self.expected_keys):
            raise ValueError("census references a different member")

    @property
    def missing_keys(self)->tuple[ResponseKey,...]:
        given={d.key for d in self.supplied}
        return tuple(k for k in self.expected_keys if k not in given)

    @property
    def is_complete(self)->bool:
        return not self.missing_keys
