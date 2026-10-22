"""C-19: three separate numerical section requests and complete bounded outputs.

No column, member, earthquake or code-compliance PASS can be expressed here.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from .quantities import Force, Moment, Length, Angle, finite_real
from .identity import EvidenceRef, RevisionRef, required
from .coordinates import LocalFrame, AxialSignConvention
from .tolerances import NumericalPolicy
from .section_models import RCSection


@dataclass(frozen=True, slots=True)
class AtStrainState:
    neutral_axis_normal: Angle
    neutral_axis_depth: Length
    def __post_init__(self):
        if type(self.neutral_axis_normal) is not Angle or type(self.neutral_axis_depth) is not Length:
            raise TypeError("angle/depth require typed quantities")
        if self.neutral_axis_depth.as_mm <= 0:
            raise ValueError("neutral axis depth must be > 0")


@dataclass(frozen=True, slots=True)
class EnvelopeAtAxialForce:
    target_compression: Force
    def __post_init__(self):
        if type(self.target_compression) is not Force:
            raise TypeError("target compression requires signed Force")


@dataclass(frozen=True, slots=True)
class RadialCapacityAtAxialForce:
    target_compression: Force
    direction_m2: Moment
    direction_m3: Moment
    def __post_init__(self):
        if type(self.target_compression) is not Force or any(
            type(m) is not Moment for m in (self.direction_m2,self.direction_m3)):
            raise TypeError("radial requires axial Force and two signed Moments")


@dataclass(frozen=True, slots=True)
class FrameModelContract:
    frame: LocalFrame
    axial_sign: AxialSignConvention
    reference: str
    def __post_init__(self):
        if type(self.frame) is not LocalFrame or type(self.axial_sign) is not AxialSignConvention:
            raise TypeError("typed local frame and axial convention required")
        required(self.reference,"reference")


@dataclass(frozen=True, slots=True)
class SectionCapacityProblem:
    section: RCSection
    request: AtStrainState | EnvelopeAtAxialForce | RadialCapacityAtAxialForce
    numerical_policy: NumericalPolicy
    frame_model_contract: FrameModelContract
    input_refs: tuple[EvidenceRef,...]
    def __post_init__(self):
        if type(self.section) is not RCSection:
            raise TypeError("RCSection required")
        if type(self.request) not in (AtStrainState,EnvelopeAtAxialForce,RadialCapacityAtAxialForce):
            raise TypeError("a supported distinct section request is required")
        if type(self.numerical_policy) is not NumericalPolicy or type(self.frame_model_contract) is not FrameModelContract:
            raise TypeError("numerical policy and frame model contract required")
        if type(self.input_refs) is not tuple or not self.input_refs or any(type(x) is not EvidenceRef for x in self.input_refs):
            raise TypeError("explicit immutable input evidence refs required")


class SectionStatus(StrEnum):
    NUMERIC_STATE="NUMERIC_STATE"
    COMPLETE_ENVELOPE="COMPLETE_ENVELOPE"
    COMPLETE_RADIAL="COMPLETE_RADIAL"
    PARTIAL_ENVELOPE="PARTIAL_ENVELOPE"
    NUMERIC_UNRESOLVED="NUMERIC_UNRESOLVED"
    UNSUPPORTED_MATERIAL="UNSUPPORTED_MATERIAL"
    UNDEFINED_MOMENT_DIRECTION="UNDEFINED_MOMENT_DIRECTION"


@dataclass(frozen=True, slots=True)
class SectionState:
    normal_angle: Angle
    c: Length
    n: Force
    m2: Moment
    m3: Moment
    axial_residual: Force | None
    sampled_root_brackets: int | None
    def __post_init__(self):
        for key,kind in (("normal_angle",Angle),("c",Length),("n",Force),
                         ("m2",Moment),("m3",Moment)):
            if type(getattr(self,key)) is not kind:
                raise TypeError(f"{key} requires {kind.__name__}")
        if self.axial_residual is not None and type(self.axial_residual) is not Force:
            raise TypeError("axial residual must be Force or None")
        if self.sampled_root_brackets is not None and (
            type(self.sampled_root_brackets) is not int or self.sampled_root_brackets < 0):
            raise ValueError("brackets must be a nonnegative integer")


@dataclass(frozen=True, slots=True)
class SectionCapacityResult:
    section_ref: RevisionRef
    request_kind: str
    status: SectionStatus
    states: tuple[SectionState,...]
    radial_capacity: Moment | None
    radial_boundary_m2: Moment | None
    radial_boundary_m3: Moment | None
    issues: tuple[str,...]
    requested_policy: NumericalPolicy
    applied_policy: NumericalPolicy
    angle_step: Angle | None
    input_refs: tuple[EvidenceRef,...]
    material_revision: RevisionRef
    law_ref: str
    kernel_ref: str
    source_geometry: tuple[tuple[str,float,str],...]
    root_quality: str
    full_column_design_pass: bool = False

    def __post_init__(self):
        if type(self.status) is not SectionStatus:
            raise TypeError("SectionStatus required")
        if type(self.states) is not tuple or any(type(x) is not SectionState for x in self.states):
            raise TypeError("states must be immutable typed tuple")
        if self.full_column_design_pass:
            raise ValueError("section pilot cannot claim full-column pass")
        if self.radial_capacity is not None and (
            self.status != SectionStatus.COMPLETE_RADIAL or
            type(self.radial_capacity) is not Moment):
            raise ValueError("radial capacity requires COMPLETE_RADIAL")
        if any("PASS" == issue for issue in self.issues):
            raise ValueError("no general code approval in section results")
