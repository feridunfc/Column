"""C-11: station geometry, immutable key, result generation and step meaning."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from .identity import required
from .quantities import Length, finite_real
from .coordinates import Point3D


class StepKind(StrEnum):
    SINGLE="SingleValue"
    ENVELOPE_MAX="EnvelopeMax"
    ENVELOPE_MIN="EnvelopeMin"
    TIME="TimeStep"
    MODE="ModeStep"


@dataclass(frozen=True, slots=True)
class StationRef:
    mapping_revision_id: str
    physical_member_id: str
    analysis_element_id: str
    station_id: str
    section_side: str
    reference_face_id: str | None = None
    physical_role: str | None = None
    def __post_init__(self):
        for key in ("mapping_revision_id","physical_member_id",
                    "analysis_element_id","station_id","section_side"):
            required(getattr(self,key),key)
        for key in ("reference_face_id","physical_role"):
            if getattr(self,key) is not None:
                required(getattr(self,key),key)


@dataclass(frozen=True, slots=True)
class StationGeometry:
    ref: StationRef
    obj_station: Length
    elm_station: Length
    physical_station: Length
    position: Point3D
    local_frame_ref: str
    matching_tol: Length
    def __post_init__(self):
        if type(self.ref) is not StationRef or type(self.position) is not Point3D:
            raise TypeError("station geometry needs StationRef and Point3D")
        for name in ("obj_station","elm_station","physical_station","matching_tol"):
            item=getattr(self,name)
            if type(item) is not Length:
                raise TypeError(f"{name} requires Length")
            if item.as_mm < 0 or (name=="matching_tol" and item.as_mm==0):
                raise ValueError(f"{name} invalid")
        required(self.local_frame_ref,"local_frame_ref")


@dataclass(frozen=True, slots=True)
class StepIdentity:
    kind: StepKind
    source_step_number: float | None = None
    source_step_label: str | None = None
    def __post_init__(self):
        if type(self.kind) is not StepKind:
            raise TypeError("StepKind required")
        if self.source_step_number is not None:
            n=finite_real(self.source_step_number)
            object.__setattr__(self,"source_step_number",n)
        if self.kind in (StepKind.TIME,StepKind.MODE) and self.source_step_number is None:
            raise ValueError("time/mode step needs numeric source index")
        if self.source_step_label is not None:
            required(self.source_step_label,"source_step_label")


@dataclass(frozen=True, slots=True)
class ResponseKey:
    run_id: str
    result_generation_id: str
    case_or_combo_id: str
    step: StepIdentity
    station: StationRef
    channel_id: str
    def __post_init__(self):
        for name in ("run_id","result_generation_id","case_or_combo_id","channel_id"):
            required(getattr(self,name),name)
        if type(self.step) is not StepIdentity or type(self.station) is not StationRef:
            raise TypeError("response key needs StepIdentity and StationRef")
