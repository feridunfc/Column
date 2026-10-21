"""S1-K: generic synthetic N/M2/M3 numerical trial pipeline.

The upstream raw snapshot is an exact case/station population. S1-E produces
A18/A19/A20-derived synthetic mechanics bases; S1-D adds minimum eccentricity
sign branches and member moment factors. Those DERIVED branches must NOT be
fed back through S1ColumnSnapshot's raw station uniqueness contract.

This layer routes derived demands directly to the retained PMM/bar-candidate
kernel. It is a numerical engineering PREVIEW, not a final TS500/TBDY check.
Real/recorded ETABS input is explicitly blocked until the separately verified
source/model/analysis and final-demand producer exists.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from math import isfinite

from .contracts import DemandKind
from .s1 import S1ColumnSnapshot, SourceClass, DemandReadiness
from .s1e_basis import S1EAxisFacts, S1EBasisStatus, prepare_s1e_basis
from .s1d_mechanics import S1DStatus, preview_ts500_static_mechanics
from .physics.rebar_layout import (
    ColumnRebarLayoutInputs, generate_rectangular_column_rebar_candidates,
)
from .physics.rebar_selection import (
    ColumnDemandBasis, ColumnDemandState, ColumnRebarSelectionPolicy,
    select_engine_rebar_for_demands,
)


class S1PipelineStatus(StrEnum):
    SOURCE_BLOCKED = "SOURCE_BLOCKED"
    BASIS_BLOCKED = "BASIS_BLOCKED"
    MECHANICS_BLOCKED = "MECHANICS_BLOCKED"
    DERIVED_POPULATION_BLOCKED = "DERIVED_POPULATION_BLOCKED"
    NO_LAYOUT_PREVIEW = "NO_LAYOUT_PREVIEW"
    NO_NUMERIC_PMM_CANDIDATE_PREVIEW = "NO_NUMERIC_PMM_CANDIDATE_PREVIEW"
    NUMERIC_CANDIDATE_PREVIEW_NOT_DESIGN_PASS = (
        "NUMERIC_CANDIDATE_PREVIEW_NOT_DESIGN_PASS"
    )


# These are implementation/engineering review gaps, not runtime-fatal
# conditions for an explicitly non-authoritative numerical experiment.
OPEN_ENGINEERING_CHECKS = (
    "MEMBER_MAXIMUM_MOMENT_AND_INTERIOR_EMIN_SCOPE_REQUIRES_TS500_REVIEW",
    "SECOND_ORDER_FACTOR_DISTRIBUTION_ALONG_MEMBER_REQUIRES_TS500_REVIEW",
    "TBDY_SHEAR_CONFINEMENT_STRONG_COLUMN_AND_JOINTS_NOT_EVALUATED",
    "NATIVE_ANALYSIS_GENERATION_AND_FINAL_DEMAND_PRODUCER_NOT_IMPLEMENTED",
)


@dataclass(frozen=True, slots=True)
class S1NumericTrial:
    column_id: str
    status: S1PipelineStatus
    reason: str
    source_class: SourceClass
    raw_station_count: int
    numeric_demand_count: int
    branch_count: int
    case_count: int
    selected_candidate_id: str | None = None
    selected_area_mm2: float | None = None
    governing_state_id: str | None = None
    governing_utilization: float | None = None
    evaluated_candidate_count: int = 0
    derived_states: tuple[ColumnDemandState, ...] = ()
    final_design_demand_proven: bool = False
    full_ts500_tbdy_design_pass: bool = False
    open_engineering_checks: tuple[str, ...] = OPEN_ENGINEERING_CHECKS


def _blocked(
    snapshot: S1ColumnSnapshot, status: S1PipelineStatus, reason: str
) -> S1NumericTrial:
    return S1NumericTrial(
        column_id=snapshot.column_id, status=status, reason=reason,
        source_class=snapshot.source_class,
        raw_station_count=len(snapshot.demands),
        numeric_demand_count=0, branch_count=0,
        case_count=len(snapshot.expected_case_ids),
    )


def run_s1_numeric_preview(
    snapshot: S1ColumnSnapshot,
    *,
    axis_facts: tuple[S1EAxisFacts, ...],
    angle_count: int = 72,
) -> S1NumericTrial:
    """One public SYNTHETIC ONLY mechanics-to-PMM calculation boundary.

    This function never alters raw demand keys, infers member I/J from station
    order, silently upgrades evidence, or publishes a design PASS. In
    particular, a fabricated review string is NOT a live ETABS authority.
    """
    if (snapshot.source_class is not SourceClass.SYNTHETIC_VALIDATION or
            snapshot.demand_readiness is not DemandReadiness.RAW_FIRST_ORDER or
            snapshot.evidence.kind is not DemandKind.SIGNED_LINEAR_STATIC):
        return _blocked(
            snapshot, S1PipelineStatus.SOURCE_BLOCKED,
            "REQUIRES_EXPLICIT_SYNTHETIC_RAW_SIGNED_STATIC_PREVIEW_SOURCE",
        )
    if snapshot.expected_station_keys is None:
        return _blocked(
            snapshot, S1PipelineStatus.SOURCE_BLOCKED,
            "EXACT_RAW_CASE_STATION_CENSUS_REQUIRED",
        )
    if angle_count < 8 or angle_count % 4:
        raise ValueError("Angle count must be >=8, divisible by four")

    mechanics = prepare_s1e_basis(snapshot, axis_facts=axis_facts)
    if (mechanics.status is not
            S1EBasisStatus.READY_SYNTHETIC_BASIS_NOT_REAL_RELEASE or
            not mechanics.automatic_numeric_basis_available or
            mechanics.real_etabs_basis_qualified):
        return _blocked(snapshot, S1PipelineStatus.BASIS_BLOCKED,
                        mechanics.reason)

    by_case = {case.output_case: case for case in mechanics.cases}
    if (len(by_case) != len(mechanics.cases) or
            set(by_case) != set(snapshot.expected_case_ids)):
        return _blocked(snapshot, S1PipelineStatus.BASIS_BLOCKED,
                        "MISSING_OR_DUPLICATE_MECHANICS_CASE")

    derived: list[ColumnDemandState] = []
    for case in snapshot.expected_case_ids:
        raw_rows = tuple(d for d in snapshot.demands if d.output_case == case)
        census = tuple(k for k in snapshot.expected_station_keys
                       if k.output_case == case)
        if not raw_rows or len(raw_rows) != len(census):
            return _blocked(snapshot, S1PipelineStatus.BASIS_BLOCKED,
                            "MISSING_CASE_STATION_ROWS")
        # Keep the original case/station census on this RAW snapshot.
        # The sign-branch population exists only as ColumnDemandState and is
        # evaluated downstream, never revalidated as a new raw snapshot.
        case_snapshot = replace(
            snapshot, expected_case_ids=(case,), expected_station_keys=census,
            demands=raw_rows,
        )
        case_basis = by_case[case]
        preview = preview_ts500_static_mechanics(
            case_snapshot, slenderness=case_basis.slenderness_basis,
            magnification=case_basis.magnification_pairs,
        )
        if (preview.status is not
                S1DStatus.NUMERIC_MECHANICS_PREVIEW_NOT_FINAL or
                preview.final_design_demand_proven or
                preview.input_state_count != len(raw_rows) or
                preview.output_state_count != len(preview.derived_states)):
            return _blocked(snapshot, S1PipelineStatus.MECHANICS_BLOCKED,
                            f"{case}:{preview.reason}")
        derived.extend(preview.derived_states)

    # Station uniqueness belongs to the RAW population. One physical station
    # may legitimately have multiple derived ±emin sign alternatives. Still,
    # no source station may be fabricated or dropped, and case/component
    # identities cannot cross or be substituted.
    raw_station_keys = {
        (d.output_case, d.station_mm / 1000.0) for d in snapshot.demands
    }
    derived_station_keys = {
        (d.output_case, d.station_m) for d in derived
    }
    if (not derived or raw_station_keys != derived_station_keys or
            len({d.state_id for d in derived}) != len(derived) or
            any(d.component_id != snapshot.column_id or
                d.output_case not in snapshot.expected_case_ids or
                not isfinite(d.nd_compression_n) or
                not isfinite(d.m2_nmm) or not isfinite(d.m3_nmm)
                for d in derived)):
        return _blocked(snapshot, S1PipelineStatus.DERIVED_POPULATION_BLOCKED,
                        "DERIVED_CASE_STATION_BRANCH_POPULATION_NOT_RECONCILED")

    population = generate_rectangular_column_rebar_candidates(
        ColumnRebarLayoutInputs(
            width_mm=snapshot.width_mm, depth_mm=snapshot.depth_mm,
            clear_cover_mm=snapshot.clear_cover_mm,
            tie_diameter_mm=snapshot.tie_diameter_mm,
            aggregate_max_mm=snapshot.aggregate_max_mm,
            allowed_bar_diameters_mm=snapshot.allowed_bar_diameters_mm,
        )
    )
    if population.status != "PROVEN":
        return _blocked(snapshot, S1PipelineStatus.NO_LAYOUT_PREVIEW,
                        "NO_FEASIBLE_REBAR_GEOMETRY_PREVIEW")

    # This basis is RESOLVED ONLY for a synthetic arithmetic experiment.
    # Its synthetic identifier can NEVER satisfy live final-demand authority;
    # the only result published here is S1NumericTrial, whose two final-pass
    # flags are fixed to False by construction.
    synthetic_basis = ColumnDemandBasis(
        analysis_order_status="RESOLVED",
        minimum_eccentricity_status="RESOLVED",
        slenderness_status="RESOLVED",
        combination_scope_status="RESOLVED",
        review_refs=("SYNTHETIC_NUMERIC_EXPERIMENT_NOT_FINAL_DESIGN",),
    )
    chosen = select_engine_rebar_for_demands(
        component_id=snapshot.column_id,
        width_mm=snapshot.width_mm, depth_mm=snapshot.depth_mm,
        population=population, material=snapshot.material,
        demands=tuple(derived), basis=synthetic_basis,
        policy=ColumnRebarSelectionPolicy(
            angle_count=angle_count, axial_tolerance_n=1.0,
        ),
    )
    selected = chosen.selected_candidate
    return S1NumericTrial(
        column_id=snapshot.column_id,
        status=(S1PipelineStatus.NUMERIC_CANDIDATE_PREVIEW_NOT_DESIGN_PASS
                if selected is not None else
                S1PipelineStatus.NO_NUMERIC_PMM_CANDIDATE_PREVIEW),
        reason=("SYNTHETIC_S1E_S1D_MULTIBRANCH_PMM_ARITHMETIC_ONLY_"
                "INTERIOR_AND_CODE_REVIEWS_OPEN"),
        source_class=snapshot.source_class,
        raw_station_count=len(snapshot.demands),
        numeric_demand_count=len(derived),
        branch_count=len(derived)-len(snapshot.demands),
        case_count=len(snapshot.expected_case_ids),
        selected_candidate_id=(selected.candidate_id if selected else None),
        selected_area_mm2=(selected.as_total_mm2 if selected else None),
        governing_state_id=chosen.governing_state_id,
        governing_utilization=chosen.governing_utilization,
        evaluated_candidate_count=len(chosen.trials),
        derived_states=tuple(derived),
    )
