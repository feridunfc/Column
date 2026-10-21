"""S1-G historical Column 235 audit. Original SHA-pinned ZIP only; no ETABS.

Checks old recorded rows, old cutset and whole-story operand comparison.
This is historical consistency evidence, never current A17–A20 or PMM authority.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from json import loads, dumps
from pathlib import Path
from zipfile import ZipFile

RECORDED = "source/docs/Column_235_Recorded_Inputs_2026-10-19.json"
CUTSET = "source/docs/COLUMN_235_CURRENT_SOURCE_AUTHORITY_CUTSET_2026-10-13.json"
STABILITY = "source/docs/COLUMN_235_STABILITY_OPERAND_COMPARISON_2026-10-19.json"

KNOWN_RECORDED_SHA = "ef700c438ec910f88ee6e05984671bdd5f5da3dc81d57d641896f92ccbe00664"
KNOWN_CUTSET_SHA = "471bbdb030aeda4c3dfaa815d5b6f5c9b3bda4da6f11ae658a1a999aef6442e9"
KNOWN_STABILITY_SHA = "1b81058eacefd50de5e79ca173a0acf2b160f00506eda1a11aee467c9acbd697"


class ArchiveEvidenceError(ValueError):
    """Original archived evidence is different, corrupt or out of scope."""


def _decimal(value, label):
    if value is None or isinstance(value, bool):
        raise ArchiveEvidenceError(f"{label}: finite numeric value required")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ArchiveEvidenceError(f"{label}: invalid number") from exc
    if not result.is_finite():
        raise ArchiveEvidenceError(f"{label}: not finite")
    return result


def _pin(blob: bytes, expected_sha: str, label: str):
    if sha256(blob).hexdigest() != expected_sha:
        raise ArchiveEvidenceError(f"{label}: ARCHIVED_SOURCE_SHA256_MISMATCH")
    return loads(blob)


@dataclass(frozen=True, slots=True)
class Column235EvidenceAudit:
    source_record_sha256: str
    source_cutset_sha256: str
    source_stability_sha256: str
    archived_frameforce_row_count: int
    single_value_row_count: int
    extrema_row_count: int
    observed_case_step_count: int
    archived_stations_mm: tuple[float, ...]
    recorded_model_sha256: str
    cutset_historical_model_sha256: str
    cutset_candidate_model_sha256: str
    model_generation_match_proven: bool
    current_b5_b6_proven: bool
    physical_regulatory_free_length_proven: bool
    current_a17_a20_proven: bool
    original_raw_m3_gravult_0_knm: float
    separate_reported_design_m3_knm: float
    moments_same_design_semantics_proven: bool
    historical_claimed_free_length_mm: float
    historical_connectivity_length_mm: float
    story_operand_difference_kn: float
    story_operand_difference_fraction: float
    global_sway_proven: bool
    modal_m6b_status: str
    required_facts: tuple[str, ...]
    status: str = "ARCHIVE_CHECKED_REAL_COLUMN_DESIGN_BLOCKED"
    full_design_authorized: bool = False

    def to_json(self) -> str:
        result = asdict(self)
        result["report_kind"] = "S1G_ARCHIVED_SOURCE_AUDIT_NOT_DESIGN_PASS"
        return dumps(result, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False)


def audit_original_235(recorded: bytes, cutset: bytes,
                       stability: bytes) -> Column235EvidenceAudit:
    """Audit exact October 2026 evidence bytes; never promote to final demands."""
    r = _pin(recorded, KNOWN_RECORDED_SHA, "original-recorded")
    c = _pin(cutset, KNOWN_CUTSET_SHA, "original-cutset")
    s = _pin(stability, KNOWN_STABILITY_SHA, "original-stability")
    if (r.get("schema") != "column.235.recorded-inputs.v1"
            or str(r.get("component_id")) != "235"
            or s.get("schema") != "column235.stability.operand-comparison.v1"
            or "REAL235" not in c.get("scope", "")):
        raise ArchiveEvidenceError("WRONG_ARCHIVE_SCOPE")
    rows = r.get("raw_frame_forces")
    if not isinstance(rows, list) or len(rows) != 60:
        raise ArchiveEvidenceError("ARCHIVED_60_ROW_POPULATION_MISMATCH")
    identities, census, stations = set(), Counter(), set()
    for row in rows:
        if (row.get("column") != "235" or row.get("element") != "235"
                or row.get("source") != "Results.FrameForce"):
            raise ArchiveEvidenceError("FORCE_COMPONENT_IDENTITY_MISMATCH")
        step = row.get("step_type")
        if step not in ("Single Value", "Max", "Min"):
            raise ArchiveEvidenceError("INVALID_STEP_SEMANTICS")
        station = _decimal(row.get("station_cm"), "station")
        local = _decimal(row.get("element_station_cm"), "element station")
        if station != local or station < 0:
            raise ArchiveEvidenceError("MEMBER_STATION_IDENTITY_MISMATCH")
        if (_decimal(row.get("n_compression_positive_kn"), "N") !=
                -_decimal(row.get("p_native_sign_kn"), "P")):
            raise ArchiveEvidenceError("ETABS_AXIAL_SIGN_CONFLICT")
        for k in ("step", "v2_kn", "v3_kn", "t_knm", "m2_knm", "m3_knm"):
            _decimal(row.get(k), k)
        identity = (row.get("case"), step, row.get("step"), str(station))
        if identity in identities:
            raise ArchiveEvidenceError("DUPLICATE_ARCHIVED_CASE_STEP_STATION")
        identities.add(identity)
        census[(row.get("case"), step)] += 1
        stations.add(station)
    if (stations != {Decimal("0"), Decimal("222.5"), Decimal("445")}
            or len(census) != 20 or any(n != 3 for n in census.values())):
        raise ArchiveEvidenceError("ARCHIVED_STATION_CASE_STEP_CENSUS_MISMATCH")
    single = sum(v for (case, step), v in census.items()
                 if step == "Single Value")
    extrema = sum(v for (case, step), v in census.items()
                  if step in ("Max", "Min"))
    if (single, extrema) != (12, 48):
        raise ArchiveEvidenceError("ARCHIVED_SIGNED_VS_EXTREMUM_SCOPE_MISMATCH")

    grav = [v for v in rows if (v["case"], v["step_type"]) ==
            ("Grav_Ult", "Single Value") and
            _decimal(v["station_cm"], "station") == 0]
    if len(grav) != 1:
        raise ArchiveEvidenceError("GRAV_ULT_FIRST_STATION_NOT_UNIQUE")
    raw_m3 = _decimal(grav[0]["m3_knm"], "raw M3")
    reported_design_m3 = _decimal(r["values"]["m3_i_knm"], "design M3")
    if raw_m3 == reported_design_m3:
        raise ArchiveEvidenceError("UNEXPECTED_DESIGN_RAW_MOMENT_EQUIVALENCE")

    ids = c["source_identities"]
    current = c["current_235_accepted"]
    if (ids.get("authority_rebound") is not False
            or current.get("B5") is not None or current.get("B6") is not None
            or c.get("GLOBAL_DELTA") != "NOT_PROVEN"
            or c.get("M6_B") != "OPEN"):
        raise ArchiveEvidenceError("OLD_ACCEPTANCE_CUTSET_CHANGED")

    if (s.get("model_sha256", "").lower() != r["edb_sha256"].lower()
            or s.get("authority") !=
            "FACTUAL_TABLE_COMPARISON_NOT_QUALIFIED_STABILITY_INPUT"
            or s.get("column_count") != 86
            or s.get("combo") != "Grav_Ult"
            or s.get("global_sway_result_issued") is not False):
        raise ArchiveEvidenceError("STORY_COMPARISON_AUTHORITY_MISMATCH")
    delta = _decimal(s["native_story_bottom_p_kn"], "story force") - _decimal(
        s["sum_design_column_compression_kn"], "column sum")
    recorded_delta = _decimal(s["difference_kn"], "difference")
    if abs(delta - recorded_delta) > Decimal("0.0001"):
        raise ArchiveEvidenceError("STORY_FORCE_OPERANDS_NOT_RECONCILED")
    relative = _decimal(s["relative_difference"], "relative difference")
    if abs(relative - delta / _decimal(
            s["sum_design_column_compression_kn"], "sum")) > Decimal("0.00000001"):
        raise ArchiveEvidenceError("STORY_FORCE_DIFFERENCE_RATIO_WRONG")

    return Column235EvidenceAudit(
        source_record_sha256=KNOWN_RECORDED_SHA,
        source_cutset_sha256=KNOWN_CUTSET_SHA,
        source_stability_sha256=KNOWN_STABILITY_SHA,
        archived_frameforce_row_count=len(rows), single_value_row_count=single,
        extrema_row_count=extrema, observed_case_step_count=len(census),
        archived_stations_mm=tuple(float(v * 10) for v in sorted(stations)),
        recorded_model_sha256=r["edb_sha256"].lower(),
        cutset_historical_model_sha256=ids["historical"].lower(),
        cutset_candidate_model_sha256=ids["candidate"].lower(),
        model_generation_match_proven=False, current_b5_b6_proven=False,
        physical_regulatory_free_length_proven=False,
        current_a17_a20_proven=False,
        original_raw_m3_gravult_0_knm=float(raw_m3),
        separate_reported_design_m3_knm=float(reported_design_m3),
        moments_same_design_semantics_proven=False,
        historical_claimed_free_length_mm=float(
            _decimal(r["values"]["free_length_mm"], "old ln")),
        historical_connectivity_length_mm=float(
            _decimal(c["historical_235_source_only"]["column"]["Length"], "L") * 1000),
        story_operand_difference_kn=float(delta),
        story_operand_difference_fraction=float(relative),
        global_sway_proven=False, modal_m6b_status="OPEN",
        required_facts=(
            "CURRENT_EDB_BYTES_MODEL_AND_RESULT_EPOCH",
            "B5_B6_COMPLETE_SIGNED_CASE_STEP_STATION_POPULATION",
            "A17_STORY_SWAY_AND_INDEPENDENT_GLOBAL_STABILITY",
            "A18_PHYSICAL_I_J_ENDS_RELEASES_AND_RESTRAINTS",
            "A19_TS500_REGULATORY_LN_K_M2_M3",
            "A20_SIGNED_END_MOMENT_AND_DESIGN_MOMENT_LINEAGE",
            "MODAL_M6B_SOURCE_AUTHORITY_AND_SECOND_ORDER_COMPOSITION",
            "FINAL_CONCURRENT_N_M2_M3_PMM_AND_REBAR_DESIGN",
        ),
    )


def audit_archive_zip(path: str | Path) -> Column235EvidenceAudit:
    with ZipFile(path) as archive:
        return audit_original_235(
            archive.read(RECORDED), archive.read(CUTSET),
            archive.read(STABILITY),
        )
