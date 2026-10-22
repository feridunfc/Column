"""Station identity != geometry != response step identity."""
from dataclasses import dataclass
from .quantities import Length, finite
from .coordinates import Point3D


def _text(v, name):
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{name} must be nonblank")


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
        for key in ("mapping_revision_id", "physical_member_id",
                    "analysis_element_id", "station_id", "section_side"):
            _text(getattr(self, key), key)
        for key in ("reference_face_id", "physical_role"):
            x = getattr(self, key)
            if x is not None: _text(x, key)


@dataclass(frozen=True, slots=True)
class StationGeometry:
    station_ref: StationRef
    object_station: Length
    element_station: Length
    physical_station: Length
    point_global: Point3D
    local_frame_ref: str
    matching_tol: Length
    def __post_init__(self):
        if type(self.station_ref) is not StationRef or type(self.point_global) is not Point3D:
            raise TypeError("requires StationRef and Point3D")
        for key in ("object_station", "element_station", "physical_station", "matching_tol"):
            v = getattr(self, key)
            if type(v) is not Length:
                raise TypeError(f"{key} requires Length")
            if v.as_mm < 0:
                raise ValueError(f"{key} cannot be negative")
        _text(self.local_frame_ref, "local_frame_ref")


_ALLOWED = frozenset({"SingleValue", "EnvelopeMax", "EnvelopeMin", "TimeStep", "ModeStep"})


@dataclass(frozen=True, slots=True)
class StepIdentity:
    step_kind: str
    step_number: float | None = None
    raw_step_label: str | None = None
    def __post_init__(self):
        if self.step_kind not in _ALLOWED:
            raise ValueError("unsupported step kind")
        if self.step_number is not None:
            object.__setattr__(self, "step_number", finite(self.step_number))
        if self.step_kind in {"TimeStep", "ModeStep"} and self.step_number is None:
            raise ValueError("indexed steps require step_number")
        if self.step_kind in {"EnvelopeMax", "EnvelopeMin", "SingleValue"} and self.step_number is not None:
            # A source may carry numeric zero for a SingleValue, so retain it.
            if self.step_kind != "SingleValue":
                raise ValueError("envelope step number requires explicit source contract")
        if self.raw_step_label is not None:
            _text(self.raw_step_label, "raw_step_label")


@dataclass(frozen=True, slots=True)
class ResponseKey:
    analysis_run_id: str
    result_generation_id: str
    case_or_combo_id: str
    step_identity: StepIdentity
    station_ref_id: str
    output_channel: str
    def __post_init__(self):
        for key in ("analysis_run_id", "result_generation_id", "case_or_combo_id",
                    "station_ref_id", "output_channel"):
            _text(getattr(self, key), key)
        if type(self.step_identity) is not StepIdentity:
            raise TypeError("step_identity requires StepIdentity")
