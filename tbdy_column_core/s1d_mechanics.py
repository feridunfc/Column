"""S1-D provisional TS 500 static member mechanics, using original TBDY math.

This is a diagnostic *preview* of slenderness, moment magnification and
minimum eccentricity, NOT an automatically certified final design demand.
No ETABS OAPI, no COM access, no hidden source promotion, no modal shortcut.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from math import isclose
from typing import Mapping

from .s1 import S1ColumnSnapshot, SourceClass, DemandReadiness
from .physics.rebar_selection import ColumnDemandState
from .physics.minimum_eccentricity import apply_ts500_minimum_eccentricity
from .physics.slenderness import (
    ColumnSlendernessBasis, evaluate_ts500_column_slenderness,
    GENERAL_SECOND_ORDER_ANALYSIS_REQUIRED,
    MOMENT_MAGNIFICATION_REQUIRED,
    SIGNED_END_MOMENT_RATIO_REQUIRED_FOR_SLENDERNESS_DECISION,
)
from .physics.moment_magnification import (
    ColumnMomentMagnificationAxisBasis,
    evaluate_ts500_axis_moment_magnification,
    magnify_concurrent_column_demand_state,
)


class S1DStatus(StrEnum):
    EVIDENCE_BLOCKED = "EVIDENCE_BLOCKED"
    MECHANICS_BASIS_BLOCKED = "MECHANICS_BASIS_BLOCKED"
    GENERAL_ANALYSIS_REQUIRED = "GENERAL_ANALYSIS_REQUIRED"
    MAGNIFICATION_BASIS_BLOCKED = "MAGNIFICATION_BASIS_BLOCKED"
    NUMERIC_MECHANICS_PREVIEW_NOT_FINAL = "NUMERIC_MECHANICS_PREVIEW_NOT_FINAL"


@dataclass(frozen=True, slots=True)
class S1DMagnificationPair:
    """Exact demand-state axis bases; never assigned by a default bool."""
    state_id: str
    m2: ColumnMomentMagnificationAxisBasis | None
    m3: ColumnMomentMagnificationAxisBasis | None


@dataclass(frozen=True, slots=True)
class S1DPreview:
    column_id: str
    status: S1DStatus
    reason: str
    input_state_count: int
    output_state_count: int
    adjusted_end_state_count: int
    intermediate_station_count: int
    axis_magnification_count: int
    derived_states: tuple[ColumnDemandState, ...] = ()
    final_design_demand_proven: bool = False


def _block(snapshot: S1ColumnSnapshot, status: S1DStatus, reason: str) -> S1DPreview:
    return S1DPreview(
        column_id=snapshot.column_id, status=status, reason=reason,
        input_state_count=len(snapshot.demands), output_state_count=0,
        adjusted_end_state_count=0, intermediate_station_count=0,
        axis_magnification_count=0,
    )


def _to_math_state(snapshot: S1ColumnSnapshot, d) -> ColumnDemandState:
    return ColumnDemandState(
        state_id=d.state_id, component_id=snapshot.column_id,
        output_case=d.output_case, case_type="SIGNED_LINEAR_STATIC",
        step_type=d.step_type,
        step_number=None if d.step_number is None else str(d.step_number),
        station_m=0.0 if d.station_mm is None else d.station_mm / 1000.0,
        end_tag=d.end_tag, nd_compression_n=d.nd_compression_n,
        m2_nmm=d.m2_nmm, m3_nmm=d.m3_nmm,
        source_identity=(
            f"{d.evidence.model_sha256}|{d.evidence.epoch_id}|"
            f"{d.evidence.analysis_generation}|{d.evidence.case_state_id}|"
            f"{d.element_id}|{d.station_mm}|{d.state_id}"
        ),
    )


def preview_ts500_static_mechanics(
    snapshot: S1ColumnSnapshot, *,
    slenderness: ColumnSlendernessBasis | None,
    magnification: tuple[S1DMagnificationPair, ...] = (),
) -> S1DPreview:
    """Evaluate trusted-input *math* only; never unlock RECORDED_ETABS PMM.

    Signed end-to-interior topology, M1/M2 ratio, l_n, k, creep/EI,
    already-applied P-Delta and analysis epoch are upstream engineering facts.
    Pure calculation here is NOT a producer or validator of those facts.
    """
    if snapshot.source_class is not SourceClass.SYNTHETIC_VALIDATION:
        return _block(snapshot, S1DStatus.EVIDENCE_BLOCKED,
                      "RECORDED_SOURCE_LACKS_QUALIFIED_GENERATION_AND_DESIGN_DEMAND")
    if snapshot.demand_readiness is not DemandReadiness.RAW_FIRST_ORDER:
        return _block(snapshot, S1DStatus.EVIDENCE_BLOCKED,
                      "INPUT_MUST_BE_RAW_FIRST_ORDER_NO_DOUBLE_MAGNIFICATION")
    if any(d.end_tag == "STATION" for d in snapshot.demands):
        return _block(snapshot, S1DStatus.EVIDENCE_BLOCKED,
                      "PHYSICAL_END_TOPOLOGY_NOT_QUALIFIED")
    if not any(d.end_tag == "I_END" for d in snapshot.demands) or not any(
        d.end_tag == "J_END" for d in snapshot.demands
    ):
        return _block(snapshot, S1DStatus.EVIDENCE_BLOCKED,
                      "END_STATE_POPULATION_UNQUALIFIED")
    if slenderness is None:
        return _block(snapshot, S1DStatus.MECHANICS_BASIS_BLOCKED,
                      "MISSING_SOURCE_BOUND_SLENDERNESS_BASIS")

    assessed = evaluate_ts500_column_slenderness(
        component_id=snapshot.column_id, basis=slenderness
    )
    axis_results = {"M2": assessed.m2, "M3": assessed.m3}
    statuses = {x.status for x in axis_results.values()}
    if GENERAL_SECOND_ORDER_ANALYSIS_REQUIRED in statuses:
        return _block(snapshot, S1DStatus.GENERAL_ANALYSIS_REQUIRED,
                      "TS500_GENERAL_SECOND_ORDER_ANALYSIS_REQUIRED")
    if SIGNED_END_MOMENT_RATIO_REQUIRED_FOR_SLENDERNESS_DECISION in statuses:
        return _block(snapshot, S1DStatus.MECHANICS_BASIS_BLOCKED,
                      "SIGNED_END_MOMENT_RATIO_NOT_SOURCE_BOUND")
    needed = {axis for axis, result in axis_results.items()
              if result.status == MOMENT_MAGNIFICATION_REQUIRED}
    required_states = {d.state_id for d in snapshot.demands}
    pairs = {p.state_id: p for p in magnification}
    if len(pairs) != len(magnification):
        return _block(snapshot, S1DStatus.MAGNIFICATION_BASIS_BLOCKED,
                      "DUPLICATE_MAGNIFICATION_STATE")
    if needed and set(pairs) != required_states:
        return _block(snapshot, S1DStatus.MAGNIFICATION_BASIS_BLOCKED,
                      "INCOMPLETE_MAGNIFICATION_DEMAND_POPULATION")
    if not needed and pairs:
        return _block(snapshot, S1DStatus.MAGNIFICATION_BASIS_BLOCKED,
                      "UNNEEDED_SECOND_ORDER_FACTORS_RISK_DOUBLE_MAGNIFICATION")

    numeric_states = []
    count = 0
    for d in snapshot.demands:
        raw = _to_math_state(snapshot, d)
        p = pairs.get(d.state_id)
        results = {"M2": None, "M3": None}
        if needed:
            assert p is not None
            for axis in ("M2", "M3"):
                basis = getattr(p, axis.lower())
                if axis not in needed:
                    if basis is not None:
                        return _block(snapshot, S1DStatus.MAGNIFICATION_BASIS_BLOCKED,
                                      "BASIS_SUPPLIED_FOR_NEGLIGIBLE_AXIS")
                    continue
                slender = axis_results[axis]
                if basis is None or (basis.axis != axis
                                    or basis.demand_state_id != d.state_id
                                    or not isclose(basis.nd_compression_n, d.nd_compression_n,
                                                   rel_tol=1e-10, abs_tol=0.01)
                                    or not isclose(basis.effective_length_lk_mm,
                                                   slender.effective_length_lk_mm,
                                                   rel_tol=1e-10, abs_tol=0.001)
                                    or not isclose(basis.radius_i_mm,
                                                   slender.radius_of_gyration_i_mm,
                                                   rel_tol=1e-10, abs_tol=0.001)
                                    or basis.sway_classification != slender.sway_classification):
                    return _block(snapshot, S1DStatus.MAGNIFICATION_BASIS_BLOCKED,
                                  "AXIS_STATE_N_K_OR_SWAY_CONTEXT_MISMATCH")
                result = evaluate_ts500_axis_moment_magnification(basis)
                if not result.applied:
                    return _block(snapshot, S1DStatus.GENERAL_ANALYSIS_REQUIRED,
                                  "TS500_MAGNIFICATION_DENOMINATOR_OR_STORY_LIMIT_BLOCKED")
                results[axis] = result
                count += 1
            raw = magnify_concurrent_column_demand_state(
                raw, m2=results["M2"], m3=results["M3"]
            )
        numeric_states.append(raw)

    # Minimum eccentricity belongs to PHYSICALLY QUALIFIED column END
    # states only. Interior stations are preserved without a fake 'end' rule.
    end_states = tuple(s for s in numeric_states
                       if s.end_tag in ("I_END", "J_END"))
    internal = tuple(s for s in numeric_states
                     if s.end_tag not in ("I_END", "J_END"))
    min_e = apply_ts500_minimum_eccentricity(
        component_id=snapshot.column_id, width_mm=snapshot.width_mm,
        depth_mm=snapshot.depth_mm, demands=end_states,
    )
    if not min_e.resolved:
        return _block(snapshot, S1DStatus.MECHANICS_BASIS_BLOCKED,
                      "MINIMUM_ECCENTRICITY_EVALUATION_UNRESOLVED")
    final_states = tuple(sorted((*min_e.states, *internal), key=lambda s: s.state_id))
    return S1DPreview(
        column_id=snapshot.column_id,
        status=S1DStatus.NUMERIC_MECHANICS_PREVIEW_NOT_FINAL,
        reason="ENGINEERING_SOURCE_AND_EQUATION_ORDERING_NEEDS_INDEPENDENT_ACCEPTANCE",
        input_state_count=len(snapshot.demands),
        output_state_count=len(final_states),
        adjusted_end_state_count=min_e.adjusted_source_state_count,
        intermediate_station_count=len(internal),
        axis_magnification_count=count, derived_states=final_states,
        final_design_demand_proven=False,
    )
