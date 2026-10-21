"""S1: preliminary signed-static longitudinal rebar and biaxial PMM assessment.

Reuses the retained pure TBDY mathematics. No ETABS access, no second-order
qualification, no full-column PASS/FAIL from this isolated step.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

from .contracts import DemandKind, EvidenceKey
from .physics.rebar_layout import ColumnRebarLayoutInputs, generate_rectangular_column_rebar_candidates
from .physics.rebar_selection import (
    ColumnDemandBasis, ColumnDemandState, ColumnRebarSelectionPolicy,
    select_engine_rebar_for_demands,
)
from .physics.section_capacity import ColumnSectionMaterial


class SourceClass(StrEnum):
    SYNTHETIC_VALIDATION = "SYNTHETIC_VALIDATION"
    RECORDED_ETABS = "RECORDED_ETABS"


class DemandReadiness(StrEnum):
    RAW_FIRST_ORDER = "RAW_FIRST_ORDER"
    FINAL_DESIGN_REVIEWED = "FINAL_DESIGN_REVIEWED"


class S1Status(StrEnum):
    DEMAND_BASIS_BLOCKED = "DEMAND_BASIS_BLOCKED"
    GEOMETRY_UNFEASIBLE = "GEOMETRY_UNFEASIBLE"
    NO_FEASIBLE_CANDIDATE = "NO_FEASIBLE_CANDIDATE"
    NUMERIC_CANDIDATE_FOUND_NOT_FULL_TBDY = "NUMERIC_CANDIDATE_FOUND_NOT_FULL_TBDY"


@dataclass(frozen=True, slots=True)
class QualifiedColumnDemand:
    state_id: str
    column_id: str
    output_case: str
    end_tag: str
    nd_compression_n: float
    m2_nmm: float
    m3_nmm: float
    evidence: EvidenceKey

    def __post_init__(self) -> None:
        if not all((self.state_id, self.column_id, self.output_case)):
            raise ValueError("Demand must have nonempty state, column, case identities")
        if self.end_tag not in ("I_END", "J_END"):
            raise ValueError("S1 only supports explicit I/J end demands")
        if not all(isfinite(x) for x in (self.nd_compression_n, self.m2_nmm, self.m3_nmm)):
            raise ValueError("Demand forces must be finite")


@dataclass(frozen=True, slots=True)
class S1ColumnSnapshot:
    column_id: str
    evidence: EvidenceKey
    source_class: SourceClass
    demand_readiness: DemandReadiness
    basis_refs: tuple[str, ...]
    width_mm: float
    depth_mm: float
    clear_cover_mm: float
    tie_diameter_mm: float
    aggregate_max_mm: float
    allowed_bar_diameters_mm: tuple[float, ...]
    material: ColumnSectionMaterial
    demands: tuple[QualifiedColumnDemand, ...]
    expected_case_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.column_id:
            raise ValueError("Missing column ID")
        if not self.demands:
            raise ValueError("No source-qualified demand states")
        if any(d.column_id != self.column_id for d in self.demands):
            raise ValueError("MIXED_COLUMN_IDENTITY")
        if len(set(d.state_id for d in self.demands)) != len(self.demands):
            raise ValueError("DUPLICATE_DEMAND_STATE")
        if len(set(self.expected_case_ids)) != len(self.expected_case_ids) or not self.expected_case_ids:
            raise ValueError("EXPECTED_CASE_UNIVERSE_INVALID")
        expected = {(case, end) for case in self.expected_case_ids for end in ("I_END", "J_END")}
        actual = {(d.output_case, d.end_tag) for d in self.demands}
        if expected != actual or len(self.demands) != len(expected):
            raise ValueError("CASE_AND_END_STATION_POPULATION_INCOMPLETE")
        for d in self.demands:
            if (
                d.evidence.model_sha256, d.evidence.epoch_id,
                d.evidence.analysis_generation, d.evidence.unit_system
            ) != (
                self.evidence.model_sha256, self.evidence.epoch_id,
                self.evidence.analysis_generation, self.evidence.unit_system
            ):
                raise ValueError("MIXED_MODEL_EPOCH_GENERATION_OR_UNITS")
            if d.evidence.case_state_id != d.output_case:
                raise ValueError("CASE_IDENTITY_MISMATCH")
            if d.evidence.kind != DemandKind.SIGNED_LINEAR_STATIC:
                raise ValueError("S1_REQUIRES_SIMULTANEOUS_SIGNED_LINEAR_STATIC_DEMAND")
        if self.evidence.kind != DemandKind.SIGNED_LINEAR_STATIC:
            raise ValueError("PROJECT_EVIDENCE_KIND_NOT_SIGNED_STATIC")
        if len(self.basis_refs) != len(set(self.basis_refs)) or any(not v for v in self.basis_refs):
            raise ValueError("basis references must be unique nonblank source identifiers")


@dataclass(frozen=True, slots=True)
class S1Result:
    column_id: str
    source_class: SourceClass
    status: S1Status
    reason: str
    evidence: EvidenceKey
    selected_candidate_id: str | None = None
    selected_area_mm2: float | None = None
    selected_bar_count: int | None = None
    governing_state_id: str | None = None
    governing_utilization: float | None = None
    evaluated_candidate_count: int = 0
    full_tbd_y_qualified: bool = False


def evaluate_s1_column(snapshot: S1ColumnSnapshot, *, angle_count: int = 72) -> S1Result:
    """Numerical candidate selection only; external design-basis proof is required.

    The function never asserts the review refs are sufficient to prove
    final demands. An adapter must separately qualify the design basis.
    """
    base = dict(column_id=snapshot.column_id, evidence=snapshot.evidence,
                source_class=snapshot.source_class)
    if snapshot.demand_readiness != DemandReadiness.FINAL_DESIGN_REVIEWED or not snapshot.basis_refs:
        return S1Result(
            **base, status=S1Status.DEMAND_BASIS_BLOCKED,
            reason="FINAL_N_M2_M3_COMBINATIONS_MIN_ECCENTRICITY_AND_SECOND_ORDER_NOT_QUALIFIED",
        )
    if angle_count < 8 or angle_count % 4:
        raise ValueError("Angle count must be >=8, divisible by four")
    params = ColumnRebarLayoutInputs(
        width_mm=snapshot.width_mm, depth_mm=snapshot.depth_mm,
        clear_cover_mm=snapshot.clear_cover_mm,
        tie_diameter_mm=snapshot.tie_diameter_mm,
        aggregate_max_mm=snapshot.aggregate_max_mm,
        allowed_bar_diameters_mm=snapshot.allowed_bar_diameters_mm,
    )
    population = generate_rectangular_column_rebar_candidates(params)
    if population.status != "PROVEN":
        return S1Result(
            **base, status=S1Status.GEOMETRY_UNFEASIBLE,
            reason="NO_BAR_LAYOUT_MEETING_BOUNDARY_AND_RHO_LIMITS",
        )
    states = tuple(
        ColumnDemandState(
            state_id=d.state_id, component_id=snapshot.column_id,
            output_case=d.output_case, case_type="SIGNED_LINEAR_STATIC",
            step_type=None, step_number=None, station_m=0.0,
            end_tag=d.end_tag, nd_compression_n=d.nd_compression_n,
            m2_nmm=d.m2_nmm, m3_nmm=d.m3_nmm,
            source_identity=(
                f"{snapshot.evidence.model_sha256}|{snapshot.evidence.epoch_id}|"
                f"{snapshot.evidence.analysis_generation}|{d.state_id}"
            ),
        ) for d in snapshot.demands
    )
    basis = ColumnDemandBasis(
        analysis_order_status="RESOLVED",
        minimum_eccentricity_status="RESOLVED",
        slenderness_status="RESOLVED",
        combination_scope_status="RESOLVED",
        review_refs=snapshot.basis_refs,
    )
    chosen = select_engine_rebar_for_demands(
        component_id=snapshot.column_id,
        width_mm=snapshot.width_mm, depth_mm=snapshot.depth_mm,
        population=population, material=snapshot.material,
        demands=states, basis=basis,
        policy=ColumnRebarSelectionPolicy(angle_count=angle_count, axial_tolerance_n=1.0),
    )
    if chosen.selected_candidate is None:
        return S1Result(
            **base, status=S1Status.NO_FEASIBLE_CANDIDATE,
            reason=chosen.status, evaluated_candidate_count=len(chosen.trials),
        )
    return S1Result(
        **base, status=S1Status.NUMERIC_CANDIDATE_FOUND_NOT_FULL_TBDY,
        reason="PMM_CANDIDATE_NUMERIC_ONLY_SEISMIC_SHEAR_CONFINEMENT_JOINT_AND_FULL_DESIGN_PENDING",
        selected_candidate_id=chosen.selected_candidate.candidate_id,
        selected_area_mm2=chosen.selected_candidate.as_total_mm2,
        selected_bar_count=chosen.selected_candidate.bar_count,
        governing_state_id=chosen.governing_state_id,
        governing_utilization=chosen.governing_utilization,
        evaluated_candidate_count=len(chosen.trials),
    )
