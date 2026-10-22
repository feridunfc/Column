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
    root_scan_samples: int | None = None
    root_min_abs_residual: Force | None = None
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
        if self.root_scan_samples is not None and (
            type(self.root_scan_samples) is not int or self.root_scan_samples <= 0):
            raise ValueError("root_scan_samples must be positive int")
        if self.root_min_abs_residual is not None and (
            type(self.root_min_abs_residual) is not Force or
            self.root_min_abs_residual.as_n < 0):
            raise ValueError("root_min_abs_residual must be nonnegative Force")


@dataclass(frozen=True, slots=True)
class AngularCoverage:
    """Exact sampled-angle coverage; not a continuous-envelope proof."""
    attempted_count: int
    resolved_indices: tuple[int,...]
    missing_indices: tuple[int,...]
    def __post_init__(self):
        if type(self.attempted_count) is not int or self.attempted_count < 8:
            raise ValueError("attempted_count must be integer >=8")
        if type(self.resolved_indices) is not tuple or type(self.missing_indices) is not tuple:
            raise TypeError("immutable tuple indices required")
        resolved=self.resolved_indices
        missing=self.missing_indices
        if any(type(x) is not int for x in (*resolved,*missing)):
            raise TypeError("angle indices must be integers")
        if resolved!=tuple(sorted(set(resolved))) or missing!=tuple(sorted(set(missing))):
            raise ValueError("angle indices must be ordered and unique")
        if set(resolved)&set(missing) or set(resolved)|set(missing)!=set(range(self.attempted_count)):
            raise ValueError("resolved/missing must partition all sampled angles")
    @property
    def is_complete(self)->bool:
        return not self.missing_indices


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
    angular_coverage: AngularCoverage | None = None
    full_column_design_pass: bool = False

    def __post_init__(self):
        if type(self.status) is not SectionStatus:
            raise TypeError("SectionStatus required")
        if type(self.states) is not tuple or any(type(x) is not SectionState for x in self.states):
            raise TypeError("states must be immutable typed tuple")
        if self.full_column_design_pass:
            raise ValueError("section pilot cannot claim full-column pass")
        if self.angular_coverage is not None and type(self.angular_coverage) is not AngularCoverage:
            raise TypeError("AngularCoverage required")
        complete=self.status in (
            SectionStatus.COMPLETE_ENVELOPE,SectionStatus.COMPLETE_RADIAL)
        if complete and (
            self.angular_coverage is None or not self.angular_coverage.is_complete
            or len(self.states)!=self.angular_coverage.attempted_count or self.issues
        ):
            raise ValueError("complete numerical result requires complete, issue-free angle coverage")
        if self.status==SectionStatus.PARTIAL_ENVELOPE and (
            self.angular_coverage is None or self.angular_coverage.is_complete
            or not self.states
        ):
            raise ValueError("partial envelope requires measured missing angles and retained states")
        if self.angular_coverage is not None and len(self.states)!=len(self.angular_coverage.resolved_indices):
            raise ValueError("resolved angular indices must match retained states")
        if self.status==SectionStatus.NUMERIC_STATE and (
            len(self.states)!=1 or self.angular_coverage is not None
        ):
            raise ValueError("direct strain state must have exactly one state without angular scan")
        if self.status==SectionStatus.UNDEFINED_MOMENT_DIRECTION and self.angular_coverage is not None:
            raise ValueError("undefined direction must not run an angular scan")
        if self.radial_capacity is not None and (
            self.status != SectionStatus.COMPLETE_RADIAL or
            type(self.radial_capacity) is not Moment):
            raise ValueError("radial capacity requires COMPLETE_RADIAL")
        if any("PASS" == issue for issue in self.issues):
            raise ValueError("no general code approval in section results")
