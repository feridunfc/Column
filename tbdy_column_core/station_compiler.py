"""S1-C: source-bound all-station factual handoff, NOT final design authority.

Consumes the old native B5 *result* only. Does not invoke COM or manufacture
minimum eccentricity, sway/second order, load combinations or accepted epoch.
"""
from __future__ import annotations

from dataclasses import dataclass

from .contracts import DemandKind, EvidenceKey
from .physics.section_capacity import ColumnSectionMaterial
from .recorded_etabs import RecordedForcePopulation, RowSemantics, RecordError
from .s1 import (DemandReadiness, DemandStationKey, QualifiedColumnDemand,
                 S1ColumnSnapshot, SourceClass)


@dataclass(frozen=True, slots=True)
class RecordedStationHandoff:
    snapshot: S1ColumnSnapshot
    expected_station_count: int
    excluded_extrema_count: int
    source_ref: str
    final_design_demand_proven: bool = False


def stage_recorded_static_column(
    population: RecordedForcePopulation, *,
    column_id: str,
    static_case_ids: tuple[str, ...],
    expected_station_keys: tuple[DemandStationKey, ...],
    claimed_evidence: EvidenceKey,
    width_mm: float, depth_mm: float, clear_cover_mm: float,
    tie_diameter_mm: float, aggregate_max_mm: float,
    allowed_bar_diameters_mm: tuple[float, ...],
    material: ColumnSectionMaterial,
) -> RecordedStationHandoff:
    """Stage every specified member/element/station, including interior ones.

    Claimed evidence and declared expected stations must be corroborated by
    the future *separate* B5 source/epoch/case/station expected-population
    authority. This function always returns RAW_FIRST_ORDER and never PASS.
    """
    if column_id not in population.column_ids:
        raise RecordError("COLUMN_ID_NOT_IN_NATIVE_CAPTURE")
    if (not static_case_ids or len(set(static_case_ids)) != len(static_case_ids)
            or not expected_station_keys
            or len(set(expected_station_keys)) != len(expected_station_keys)):
        raise RecordError("EXPECTED_STATIC_STATION_SCOPE_REQUIRED")
    if {s.output_case for s in expected_station_keys} != set(static_case_ids):
        raise RecordError("EXPECTED_STATIC_CASE_STATION_SCOPE_MISMATCH")
    if claimed_evidence.kind != DemandKind.SIGNED_LINEAR_STATIC:
        raise RecordError("SOURCE_EVIDENCE_MUST_BE_EXPLICIT_STATIC_CLAIM")
    selected = tuple(r for r in population.rows
                     if r.column_id == column_id and r.case_name in static_case_ids)
    if not selected:
        raise RecordError("NO_NATIVE_ROWS_FOR_REQUIRED_CASE_SCOPE")
    if any(r.semantics is not RowSemantics.SINGLE_VALUE_NEEDS_CASE_AUTHORITY
           for r in selected):
        raise RecordError("NON_SIMULTANEOUS_ENVELOPE_IN_REQUIRED_CASE_SCOPE")
    actual = tuple(DemandStationKey(r.case_name, r.element_id,
                                    r.station_mm, r.element_station_mm) for r in selected)
    if len(set(actual)) != len(actual) or set(actual) != set(expected_station_keys):
        raise RecordError("MISSING_EXTRA_OR_DUPLICATE_NATIVE_STATION")
    rows = []
    for r in sorted(selected, key=lambda x: (x.case_name, x.element_id,
                                              x.station_mm, x.element_station_mm)):
        state_id = (f"{column_id}|{r.case_name}|{r.element_id}|"
                    f"{r.station_mm:.9f}|{r.element_station_mm:.9f}|"
                    f"{r.step_type}|{r.step_number}")
        rows.append(QualifiedColumnDemand(
            state_id=state_id, column_id=column_id, output_case=r.case_name,
            end_tag="STATION", nd_compression_n=r.n_compression_n,
            m2_nmm=r.m2_nmm, m3_nmm=r.m3_nmm,
            evidence=EvidenceKey(
                model_sha256=claimed_evidence.model_sha256,
                epoch_id=claimed_evidence.epoch_id,
                analysis_generation=claimed_evidence.analysis_generation,
                case_state_id=r.case_name, kind=DemandKind.SIGNED_LINEAR_STATIC,
            ),
            station_mm=r.station_mm, element_id=r.element_id,
            element_station_mm=r.element_station_mm, step_type=r.step_type,
            step_number=r.step_number,
        ))
    snapshot = S1ColumnSnapshot(
        column_id=column_id, evidence=claimed_evidence,
        source_class=SourceClass.RECORDED_ETABS,
        demand_readiness=DemandReadiness.RAW_FIRST_ORDER,
        basis_refs=(), width_mm=width_mm, depth_mm=depth_mm,
        clear_cover_mm=clear_cover_mm, tie_diameter_mm=tie_diameter_mm,
        aggregate_max_mm=aggregate_max_mm,
        allowed_bar_diameters_mm=allowed_bar_diameters_mm,
        material=material, demands=tuple(rows), expected_case_ids=static_case_ids,
        expected_station_keys=expected_station_keys,
    )
    excluded = sum(r.column_id == column_id and
                   r.semantics is RowSemantics.MODAL_OR_EXTREMUM_NOT_SIMULTANEOUS
                   for r in population.rows)
    return RecordedStationHandoff(
        snapshot=snapshot, expected_station_count=len(expected_station_keys),
        excluded_extrema_count=excluded, source_ref=population.source_ref,
    )
