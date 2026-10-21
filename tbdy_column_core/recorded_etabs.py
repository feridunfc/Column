"""S1-B read-only bridge to the ORIGINAL TBDY ETABS factual reader output.

This module NEVER connects to ETABS, issues OAPI calls, or certifies final PMM.
On Windows the unchanged existing providers own COM, results selection and restore.
In Codespaces their typed factual output and historical recorded rows can be replayed.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from math import isclose, isfinite
from pathlib import Path
from typing import Any, Mapping
import json


class RecordError(ValueError):
    """Native record is missing, inconsistent, unsupported, or unqualified."""


class RowSemantics(StrEnum):
    SINGLE_VALUE_NEEDS_CASE_AUTHORITY = "SINGLE_VALUE_NEEDS_CASE_AUTHORITY"
    MODAL_OR_EXTREMUM_NOT_SIMULTANEOUS = "MODAL_OR_EXTREMUM_NOT_SIMULTANEOUS"


@dataclass(frozen=True, slots=True)
class RecordedForce:
    column_id: str
    element_id: str
    case_name: str
    step_type: str
    step_number: float | None
    station_mm: float
    element_station_mm: float
    n_compression_n: float
    v2_n: float
    v3_n: float
    torsion_nmm: float
    m2_nmm: float
    m3_nmm: float
    semantics: RowSemantics
    source_api: str = "Results.FrameForce"


@dataclass(frozen=True, slots=True)
class RecordedForcePopulation:
    origin: str
    column_ids: tuple[str, ...]
    edb_sha256_claim: str | None
    source_ref: str
    rows: tuple[RecordedForce, ...]
    native_population_proven: bool
    final_design_demand_proven: bool = False

    def __post_init__(self) -> None:
        if not self.rows or not self.column_ids:
            raise RecordError("EMPTY_COLUMN_FORCE_POPULATION")
        if set(r.column_id for r in self.rows) != set(self.column_ids):
            raise RecordError("COLUMN_POPULATION_MISMATCH")
        keys = [(r.column_id, r.element_id, r.case_name, r.step_type,
                 r.step_number, r.station_mm, r.element_station_mm) for r in self.rows]
        if len(keys) != len(set(keys)):
            raise RecordError("DUPLICATE_EXACT_FORCE_ROW")
        if self.final_design_demand_proven:
            raise RecordError("ADAPTER_CANNOT_CERTIFY_FINAL_DESIGN_DEMAND")

    @property
    def single_value_rows(self) -> tuple[RecordedForce, ...]:
        return tuple(r for r in self.rows
                     if r.semantics is RowSemantics.SINGLE_VALUE_NEEDS_CASE_AUTHORITY)

    @property
    def extrema_rows(self) -> tuple[RecordedForce, ...]:
        return tuple(r for r in self.rows
                     if r.semantics is RowSemantics.MODAL_OR_EXTREMUM_NOT_SIMULTANEOUS)

    def summary(self) -> dict[str, object]:
        return {
            "origin": self.origin,
            "column_ids": list(self.column_ids),
            "source_ref": self.source_ref,
            "edb_sha256_claim": self.edb_sha256_claim,
            "raw_force_count": len(self.rows),
            "single_value_row_count": len(self.single_value_rows),
            "extrema_row_count": len(self.extrema_rows),
            "cases_and_step_types": [
                {"case": c, "step_type": s}
                for c, s in sorted({(r.case_name, r.step_type) for r in self.rows})
            ],
            "stations_mm": sorted({r.station_mm for r in self.rows}),
            "native_population_proven": self.native_population_proven,
            "final_design_demand_proven": False,
            "engineering_release_qualified": False,
            "blockers": [
                "CURRENT_ANALYSIS_GENERATION_AND_MODEL_BINDING_NOT_PROVEN",
                "COMPLETE_DESIGN_COMBINATION_AND_STATION_UNIVERSE_NOT_PROVEN",
                "MINIMUM_ECCENTRICITY_AND_SECOND_ORDER_NOT_PROVEN",
                "S1_I_J_ONLY_CANNOT_SILENTLY_DROP_INTERIOR_STATION",
            ],
        }


def _txt(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise RecordError(f"{label}: canonical nonblank text required")
    return value


def _num(value: object, label: str) -> float:
    if value is None or isinstance(value, bool):
        raise RecordError(f"{label}: finite numeric value required")
    try:
        d = Decimal(str(value))
    except (ValueError, InvalidOperation) as exc:
        raise RecordError(f"{label}: not numeric") from exc
    if not d.is_finite():
        raise RecordError(f"{label}: nonfinite")
    result = float(d)
    if not isfinite(result):
        raise RecordError(f"{label}: outside finite range")
    return result


def _history_row(raw: Mapping[str, Any]) -> RecordedForce:
    if _txt(raw.get("source"), "source") != "Results.FrameForce":
        raise RecordError("NOT_RESULTS_FRAME_FORCE")
    p = _num(raw.get("p_native_sign_kn"), "p_native_sign_kn")
    n = _num(raw.get("n_compression_positive_kn"), "n_compression_positive_kn")
    if not isclose(-p, n, rel_tol=1e-10, abs_tol=1e-6):
        raise RecordError("NATIVE_P_SIGN_CONFLICT")
    step = _txt(raw.get("step_type"), "step_type")
    if step == "Single Value":
        semantics = RowSemantics.SINGLE_VALUE_NEEDS_CASE_AUTHORITY
    elif step in ("Max", "Min"):
        semantics = RowSemantics.MODAL_OR_EXTREMUM_NOT_SIMULTANEOUS
    else:
        raise RecordError("UNSUPPORTED_STEP_SEMANTICS")
    return RecordedForce(
        column_id=_txt(raw.get("column"), "column"),
        element_id=_txt(raw.get("element"), "element"),
        case_name=_txt(raw.get("case"), "case"),
        step_type=step, step_number=_num(raw.get("step"), "step"),
        station_mm=_num(raw.get("station_cm"), "station_cm") * 10,
        element_station_mm=_num(raw.get("element_station_cm"), "element_station_cm") * 10,
        n_compression_n=n * 1000,
        v2_n=_num(raw.get("v2_kn"), "v2_kn") * 1000,
        v3_n=_num(raw.get("v3_kn"), "v3_kn") * 1000,
        torsion_nmm=_num(raw.get("t_knm"), "t_knm") * 1_000_000,
        m2_nmm=_num(raw.get("m2_knm"), "m2_knm") * 1_000_000,
        m3_nmm=_num(raw.get("m3_knm"), "m3_knm") * 1_000_000,
        semantics=semantics,
    )


def import_historical_column_capture(payload: Mapping[str, Any]) -> RecordedForcePopulation:
    """Import old Column_235_Recorded_Inputs raw_force_rows without claiming B5 freshness.

    Expected row count, case/step census and stations check file consistency.
    Historical fixture *cannot* certify real ETABS source/generation/combination scope.
    """
    if payload.get("schema") != "column.s1b.historical.frame_force.v1":
        raise RecordError("UNSUPPORTED_HISTORICAL_RECORD_SCHEMA")
    source_rows = payload.get("raw_frame_forces")
    if not isinstance(source_rows, list) or not source_rows:
        raise RecordError("MISSING_RAW_FRAME_FORCE_ROWS")
    rows = tuple(_history_row(r) for r in source_rows)
    n_expected = payload.get("expected_row_count")
    if type(n_expected) is not int or n_expected != len(rows):
        raise RecordError("HISTORICAL_ROW_COUNT_MISMATCH")
    expected_steps = payload.get("expected_case_steps")
    if not isinstance(expected_steps, list) or not expected_steps:
        raise RecordError("MISSING_CASE_STEP_CENSUS")
    census = [(_txt(s["case"], "case"), _txt(s["step_type"], "step")) for s in expected_steps]
    if len(census) != len(set(census)) or set(census) != {
        (r.case_name, r.step_type) for r in rows
    }:
        raise RecordError("CASE_STEP_POPULATION_MISMATCH")
    expected_stations = payload.get("expected_station_cm")
    if not isinstance(expected_stations, list) or not expected_stations:
        raise RecordError("MISSING_STATION_CENSUS")
    stations = [_num(s, "expected station") * 10 for s in expected_stations]
    if len(stations) != len(set(stations)):
        raise RecordError("DUPLICATE_EXPECTED_STATION")
    # Explicit duplicate check before missing-station/case errors.
    keys = [(r.column_id, r.element_id, r.case_name, r.step_type,
             r.step_number, r.station_mm, r.element_station_mm) for r in rows]
    if len(keys) != len(set(keys)):
        raise RecordError("DUPLICATE_EXACT_FORCE_ROW")
    counts = Counter((r.case_name, r.step_type) for r in rows)
    for state in census:
        got = {r.station_mm for r in rows if (r.case_name, r.step_type) == state}
        if got != set(stations) or counts[state] != len(stations):
            raise RecordError("STATION_POPULATION_MISMATCH")
    name = _txt(payload.get("column_unique_name"), "column_unique_name")
    if any(r.column_id != name for r in rows):
        raise RecordError("COLUMN_IDENTITY_MISMATCH")
    sha = _txt(payload.get("reported_edb_sha256_unverified"), "edb sha")
    if len(sha) != 64 or any(ch.lower() not in "0123456789abcdef" for ch in sha):
        raise RecordError("MALFORMED_REPORTED_EDB_SHA")
    return RecordedForcePopulation(
        origin="HISTORICAL_CAPTURE_NO_CURRENT_GENERATION",
        column_ids=(name,), edb_sha256_claim=sha,
        source_ref=_txt(payload.get("original_file_sha256"), "original_file_sha256"),
        rows=rows, native_population_proven=False,
    )


def read_historical_column_capture(path: str | Path) -> RecordedForcePopulation:
    return import_historical_column_capture(json.loads(Path(path).read_text(encoding="utf-8")))


def import_old_b5_force_population(fact: object, *, source_unit: str) -> RecordedForcePopulation:
    """Reuse unchanged old ColumnForceResultPopulationFact; NO second COM stack.

    Original instance has .rows. Its .as_dict() drops rows and is insufficient.
    Native B5 provider proves returned population, not finished second-order PMM.
    """
    if getattr(fact, "contract", None) != "TBDY_B5_COLUMN_FORCE_RESULT_POPULATION_V1":
        raise RecordError("NOT_OLD_B5_COLUMN_FORCE_RESULT_POPULATION")
    if source_unit != "kN_cm_kNm":
        raise RecordError("NATIVE_DISPLAY_UNITS_NOT_EXPLICITLY_QUALIFIED")
    case = _txt(getattr(fact, "case_name", None), "case_name")
    expected = tuple(getattr(fact, "expected_unique_names", ()))
    observed = tuple(getattr(fact, "observed_unique_names", ()))
    if not expected or sorted(expected) != sorted(observed) or len(set(expected)) != len(expected):
        raise RecordError("B5_EXPECTED_COLUMN_POPULATION_MISMATCH")
    rows: list[RecordedForce] = []
    for raw in getattr(fact, "rows", ()):
        if not isinstance(raw, Mapping):
            raise RecordError("OLD_B5_ROW_NOT_MAPPING")
        if _txt(raw.get("OutputCase"), "OutputCase") != case:
            raise RecordError("OLD_B5_OUTPUT_CASE_MISMATCH")
        kind, step = _txt(raw.get("CaseType"), "CaseType"), raw.get("StepType")
        if kind == "LinStatic" and step in (None, "", "Single Value"):
            sem = RowSemantics.SINGLE_VALUE_NEEDS_CASE_AUTHORITY
            step = "Single Value"
        elif kind == "LinRespSpec" and step in ("Max", "Min"):
            sem = RowSemantics.MODAL_OR_EXTREMUM_NOT_SIMULTANEOUS
        else:
            raise RecordError("OLD_B5_UNSUPPORTED_CASE_OR_STEP_SEMANTICS")
        rows.append(RecordedForce(
            column_id=_txt(raw.get("UniqueName"), "UniqueName"),
            element_id=_txt(raw.get("Element"), "Element"),
            case_name=case, step_type=str(step),
            step_number=None if raw.get("StepNumber") is None else _num(raw["StepNumber"], "StepNumber"),
            station_mm=_num(raw.get("Station"), "Station") * 10,
            element_station_mm=_num(raw.get("ElemStation"), "ElemStation") * 10,
            n_compression_n=-_num(raw.get("P"), "P") * 1000,
            v2_n=_num(raw.get("V2"), "V2") * 1000,
            v3_n=_num(raw.get("V3"), "V3") * 1000,
            torsion_nmm=_num(raw.get("T"), "T") * 1_000_000,
            m2_nmm=_num(raw.get("M2"), "M2") * 1_000_000,
            m3_nmm=_num(raw.get("M3"), "M3") * 1_000_000,
            semantics=sem,
        ))
    return RecordedForcePopulation(
        origin="ORIGINAL_B5_PROVIDER_NO_FINAL_DESIGN_QUALIFICATION",
        column_ids=tuple(sorted(expected)),
        edb_sha256_claim=None,
        source_ref=_txt(getattr(fact, "evidence_ref", None), "evidence_ref"),
        rows=tuple(rows), native_population_proven=True,
    )


def recorded_force_report_json(population: RecordedForcePopulation) -> str:
    return json.dumps(population.summary(), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)
