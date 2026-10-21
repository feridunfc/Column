"""S1-H: source-pinned offline recovery vs future gateway acquisition routing.

Uses REAL archived October 2026 Column 235 documents as evidence, not a
made-up mock acceptance. Never reads an EDB or performs native ETABS calls.
All acceptance flags remain false. This module plans the work only.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import StrEnum
from hashlib import sha256
from json import dumps, loads
from pathlib import Path
from typing import Mapping
from zipfile import ZipFile

from .s1g_archive import audit_original_235, RECORDED, CUTSET, STABILITY


class S1HError(ValueError):
    """Missing or conflicting original evidence. No fallback to user labels."""


class Lane(StrEnum):
    ARCHIVED_ONLY = "ARCHIVED_ONLY_NOT_CURRENT_AUTHORITY"
    OFFLINE_PROJECT_DOCUMENT_REVIEW = "OFFLINE_PROJECT_DOCUMENT_REVIEW"
    OFFLINE_FILE_OR_EXPORT_SEARCH = "OFFLINE_FILE_OR_EXPORT_SEARCH"
    OFFLINE_FACT_RECONCILIATION = "OFFLINE_FACT_RECONCILIATION"
    FUTURE_GATEWAY_IF_EXPORT_ABSENT = "FUTURE_GATEWAY_IF_EXPORT_ABSENT"
    DERIVE_AFTER_PREREQUISITES = "DERIVE_AFTER_PREREQUISITES"


@dataclass(frozen=True, slots=True)
class RecoveryItem:
    id: str
    lane: Lane
    status: str
    source_documents: tuple[str, ...]
    observed: str
    authority_limit: str
    next_action: str
    future_gateway_capture: str | None = None
    prerequisites: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class S1HRecoveryPlan:
    schema: str
    component_id: str
    status: str
    source_digest_sha256: dict[str, str]
    original_235_frameforce_rows: int
    preserved_native_fact_count: int
    archive_document_count: int
    candidate_model_sha256: str
    recorded_model_sha256: str
    source_models_rebound: bool
    full_project_design_proven: bool
    etabs_live_executed: bool
    items: tuple[RecoveryItem, ...]
    offline_search_inventory: tuple[str, ...]
    future_capture_order: tuple[str, ...]
    release_blockers: tuple[str, ...]

    def json(self) -> str:
        return dumps(asdict(self), ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False)


# Exact ORIGINAL source bytes from TBDY_COLUMN_EXTERNAL_AUDIT_2026-10-20.zip.
# Git SHA identities in documentation are NOT equivalent to these byte hashes.
PINNED = {
    RECORDED: "ef700c438ec910f88ee6e05984671bdd5f5da3dc81d57d641896f92ccbe00664",
    CUTSET: "471bbdb030aeda4c3dfaa815d5b6f5c9b3bda4da6f11ae658a1a999aef6442e9",
    STABILITY: "1b81058eacefd50de5e79ca173a0acf2b160f00506eda1a11aee467c9acbd697",
    "source/docs/COLUMN_235_REAL_INPUT_AUTHORITY_SNAPSHOT_2026-10-14.json":
        "be29c33e7b4bab4bc78aa08888f250caf01ab95239a14317a4253120e72f20c4",
    "source/docs/COLUMN_235_FIRST_REAL_INPUT_PRODUCT_READINESS_RECEIPT_2026-10-14.json":
        "5afc17ca08136dd23a48a3e82139fd03d7e8e2c56b7bb3c4af22f4e2271795a7",
    "source/docs/COLUMN_235_USER_GEOMETRY_DECLARATION_2026-10-14.json":
        "b8d6440189f3ed2705d4565edf10a6b55d1a6ed2c030f271818ba9e5b682e6f0",
    "source/docs/COLUMN_235_ABI7_LIVE_COORDINATES_ADOPTION_2026-10-14.json":
        "75370f7d0c2442d9e66422967d149a5e110e823a058ccb18b0fd698bf4495730",
    "source/docs/COLUMN_R1_R3M_ABI4_LIVE_GETSECTION_ADOPTION_2026-10-12.json":
        "b0cdb95c434c9f9ab3c8fb6cfcbfb3c529aa9b981578081ceb935a7b3a644278",
    "source/docs/COLUMN_R1_R3M_ABI5_LIVE_GETSECTPROPS_ADOPTION_2026-10-12.json":
        "79ba4dc212c6b39283362d292152acb77003467f1b620a13e2790f6be221ea2e",
}

CUT = CUTSET
REC = RECORDED
STAB = STABILITY
AUTH = "source/docs/COLUMN_235_REAL_INPUT_AUTHORITY_SNAPSHOT_2026-10-14.json"
READY = "source/docs/COLUMN_235_FIRST_REAL_INPUT_PRODUCT_READINESS_RECEIPT_2026-10-14.json"
DECL = "source/docs/COLUMN_235_USER_GEOMETRY_DECLARATION_2026-10-14.json"
COORD = "source/docs/COLUMN_235_ABI7_LIVE_COORDINATES_ADOPTION_2026-10-14.json"
ASSIGN = "source/docs/COLUMN_R1_R3M_ABI4_LIVE_GETSECTION_ADOPTION_2026-10-12.json"
INERT = "source/docs/COLUMN_R1_R3M_ABI5_LIVE_GETSECTPROPS_ADOPTION_2026-10-12.json"

SOURCE_PRODUCERS = (
    "source/packages/etabs_gateway/src/etabs_gateway/replay.py",
    "source/tbdy_engine/application/column_stability_runtime.py",
    "source/tbdy_engine/application/column_a18_end_restraint.py",
    "source/tbdy_engine/application/column_a19_effective_length.py",
    "source/tbdy_engine/application/column_a20_end_moment_ratio.py",
)


def _equal(actual: object, expected: object, code: str) -> None:
    if actual != expected:
        raise S1HError(code)


def _safe_json(blobs: Mapping[str, bytes], name: str) -> dict:
    try:
        data = blobs[name]
    except KeyError as exc:
        raise S1HError(f"MISSING_PINNED_SOURCE:{name}") from exc
    if sha256(data).hexdigest() != PINNED[name]:
        raise S1HError(f"PINNED_SOURCE_CHANGED:{name}")
    try:
        parsed = loads(data)
    except (ValueError, UnicodeError) as exc:
        raise S1HError(f"INVALID_PINNED_JSON:{name}") from exc
    if not isinstance(parsed, dict):
        raise S1HError(f"INVALID_PINNED_ROOT:{name}")
    return parsed


def derive_recovery_plan(
    originals: Mapping[str, bytes], *,
    archive_members: tuple[str, ...] = (),
) -> S1HRecoveryPlan:
    """Deterministic authority-limited inventory from exact source bytes.

    Source documents are accepted ONLY as records *of what was observed*.
    Their absence of current proof is not a proof that another offline export
    cannot exist. We do not mark new ETABS acquisition unconditionally needed.
    """
    parsed = {name: _safe_json(originals, name) for name in PINNED}
    # S1-G independent pinned case/station/sign/stability census.
    try:
        prior = audit_original_235(
            originals[REC], originals[CUT], originals[STAB]
        )
    except (ValueError, TypeError, KeyError) as exc:
        raise S1HError(f"S1G_ORIGINAL_AUDIT_REJECTED:{exc}") from exc

    cut, authority, ready = parsed[CUT], parsed[AUTH], parsed[READY]
    decl, coords, archived = parsed[DECL], parsed[COORD], parsed[REC]
    model = cut["source_identities"]["candidate"].lower()
    recorded = archived["edb_sha256"].lower()
    _equal(cut["source_identities"]["authority_rebound"], False,
           "UNEXPECTED_CANDIDATE_REBOUND")
    _equal(authority["source_checkpoint"]["candidate_sha256"].lower(), model,
           "AUTHORITY_MODEL_DISAGREES_WITH_CUTSET")
    _equal(ready["source"]["candidate_EDB_sha256"].lower(), model,
           "READINESS_MODEL_DISAGREES_WITH_CUTSET")
    _equal(coords["source"]["candidate_sha256"].lower(), model,
           "COORDINATE_MODEL_DISAGREES_WITH_CUTSET")
    _equal(decl["candidate_EDB_sha256"].lower(), model,
           "DECLARATION_MODEL_DISAGREES_WITH_CUTSET")
    if model == recorded or prior.model_generation_match_proven:
        raise S1HError("UNEXPECTED_MODEL_SOURCE_EQUIVALENCE")

    native = authority.get("accepted_native_facts", [])
    expected_keys = {
        "section_assignment", "I22", "I33",
        "Point1_Global_xyz", "Point2_Global_xyz",
    }
    if (not isinstance(native, list) or len(native) != 5 or
            {x.get("field") for x in native} != expected_keys or
            any(x.get("source_kind") != "ACCEPTED_NATIVE_FACT_LIMITED_SCOPE"
                for x in native)):
        raise S1HError("LIMITED_SCOPE_NATIVE_FACT_CENSUS_CHANGED")
    facts = {f["field"]: f for f in native}
    _equal(facts["section_assignment"]["value"],
           cut["current_235_accepted"]["section_assignment"],
           "SECTION_ASSIGNMENT_DISAGREEMENT")
    for axis in ("I22", "I33"):
        _equal(float(facts[axis]["value"]),
               float(cut["current_235_accepted"][axis]["value"]),
               f"INERTIA_{axis}_DISAGREEMENT")
        _equal(facts[axis]["unit"], "m^4", f"INERTIA_{axis}_UNIT_MISMATCH")
    ps = {x["native_slot"]: x for x in coords["points"]}
    _equal(set(ps), {"Point1", "Point2"}, "MISSING_NATIVE_POINT")
    for idx in ("Point1", "Point2"):
        expected = facts[f"{idx}_Global_xyz"]["value"]
        observed = ps[idx]
        if (str(expected["point_name"]) != str(observed["point_name"])
                or expected["X"] != observed["X"]
                or expected["Y"] != observed["Y"]
                or expected["Z"] != observed["Z"]
                or observed["unit"] != "m"):
            raise S1HError("NATIVE_COORDINATE_DISAGREEMENT")
    length_mm = abs(ps["Point2"]["Z"] - ps["Point1"]["Z"]) * 1000
    if length_mm != 5150.0:
        raise S1HError("SOURCE_CONNECTIVITY_LENGTH_CHANGED")
    _equal(coords["qualification_limits"]["regulatory_ln"],
           "NOT_DERIVED", "LENGTH_5150_NOT_TS500_LN")
    _equal(coords["observed_integrity"]["model_fingerprint"], None,
           "MODEL_FINGERPRINT_AUTHORITY_CHANGED")

    _equal(decl["source_kind"], "USER_DECLARATION_NOT_PROJECT_VERIFIED",
           "USER_DECLARATION_WRONGLY_ACCEPTED")
    _equal(decl["review"]["status"], "NOT_RECORDED",
           "PROJECT_REVIEW_STATUS_CHANGED")
    _equal(decl["declared"]["width_local_2_cm"], 80,
           "USER_DECLARED_WIDTH_CHANGED")
    _equal(decl["declared"]["depth_local_3_cm"], 80,
           "USER_DECLARED_DEPTH_CHANGED")
    _equal(ready["real_235"]["first_leaf_status"],
           "NOT_COMPUTED_MISSING_PROJECT_REVIEWED_INPUT",
           "FIRST_LEAF_STATUS_CHANGED")
    _equal(ready["real_235"]["full_design_ready"], False,
           "UNEXPECTED_235_FULL_DESIGN_READY")
    _equal(set(ready["real_235"]["missing_fields"]),
           {"width_mm", "depth_mm", "axis_basis"},
           "FIRST_LEAF_MISSING_GEOMETRY_CHANGED")

    fields = authority["fields"]
    if len(fields) != 38 or any(f.get("value") is not None for f in fields):
        raise S1HError("OLD_INPUT_MATRIX_IS_NOT_EMPTY_AS_RECORDED")
    accepted = cut["current_235_accepted"]
    if (accepted["B5"] is not None or accepted["B6"] is not None or
            accepted["current_result_epoch"] != "NOT_QUALIFIED" or
            cut["GLOBAL_DELTA"] != "NOT_PROVEN" or cut["M6_B"] != "OPEN"):
        raise S1HError("CURRENT_RESULT_AUTHORITY_UNEXPECTEDLY_CHANGED")

    items = (
        RecoveryItem(
            "H01", Lane.ARCHIVED_ONLY, "PRESENT_AS_HISTORICAL_CAPTURE",
            (REC,), "60 old FrameForce rows, 12 single-value, 48 Max/Min, three stations",
            "Different source model SHA; maxima/minima are not concurrent signed demand",
            "Preserve/read all original old force rows offline; do not promote to candidate",
            prerequisites=(),
        ),
        RecoveryItem(
            "H02", Lane.ARCHIVED_ONLY, "FIVE_OLD_NATIVE_FACTS_LIMITED_SCOPE",
            (AUTH, COORD, ASSIGN, INERT),
            "Column_80x80; I22=I33=0.03413333333333332 m^4; "
            "Point1=955 at Z=-5.15m, Point2=758 at Z=0m",
            "Assignment/inertia/point coordinates alone do not prove physical ends, "
            "section b/h, local axis signs, regulatory ln or analysis generation",
            "Retain native fact receipts and reconcile source revisions offline",
        ),
        RecoveryItem(
            "H03", Lane.OFFLINE_PROJECT_DOCUMENT_REVIEW,
            "DECLARED_800X800_NOT_PROJECT_REVIEWED",
            (DECL, READY, AUTH),
            "User declares 800×800 mm and local-2 parallel X; no local-axis signs",
            "Review metadata (document/revision/reviewer/time) NOT_RECORDED",
            "Use project drawing or already saved reviewed document to qualify b/h "
            "and local axis orientations offline, without forcing new ETABS acquisition",
        ),
        RecoveryItem(
            "H04", Lane.OFFLINE_FILE_OR_EXPORT_SEARCH,
            "CANDIDATE_EDB_DIGEST_CLAIM_WITHOUT_REBOUND",
            (CUT, COORD, AUTH),
            "Old native candidate ID and historical old-force ID are different",
            "EDB path/old digest claims do not bind in-memory result generation",
            "Look for exact candidate .EDB bytes and hash locally, plus matching "
            "analysis-generation capture, original sidecars and immutable epoch",
            future_gateway_capture="If no matching generation evidence is retained, "
                                   "capture source/model/analysis fingerprint on a later "
                                   "authorized gateway session",
        ),
        RecoveryItem(
            "H05", Lane.FUTURE_GATEWAY_IF_EXPORT_ABSENT,
            "CURRENT_B5_B6_ABSENT_IN_SCOPED_RECEIPTS",
            (CUT, READY, REC),
            "Candidate B5=None, B6=None; previous 60 results are historical",
            "Old signed static rows and modal Max/Min cannot be silently joined",
            "Search for independently complete same-generation B5/B6 original "
            "exports (case, step, station, member census) before any new acquisition",
            future_gateway_capture="Capture B5/B6 once through EXISTING ETABS gateway "
                                   "after explicit Windows authorization",
            prerequisites=("H04",),
        ),
        RecoveryItem(
            "H06", Lane.OFFLINE_FACT_RECONCILIATION,
            "CONFLICTING_STORY_FORCE_OPERANDS",
            (STAB,), "86-column sum=194176.996 kN, story native=276640.2736 kN",
            "82,463.2776 kN difference; 42.4681% against column sum; "
            "not a global sway or story-shear qualification",
            "Reconcile output case, element/story population, station grain, "
            "compression sign and result generation using old tables offline; "
            "otherwise capture coherent story/column forces later",
            prerequisites=("H04", "H05"),
        ),
        RecoveryItem(
            "H07", Lane.FUTURE_GATEWAY_IF_EXPORT_ABSENT,
            "A17_GLOBAL_SWAY_NOT_QUALIFIED",
            (CUT, STAB), "GLOBAL_DELTA NOT_PROVEN, old story result not issued",
            "Sway classification needs compatible story displacement/shear and "
            "column population across both axes; never default no-sway",
            "Search existing A17/TS500 story-sway factual exports and source tables "
            "from same current epoch; resolve H06 before numerical qualification",
            future_gateway_capture="Acquire complete same-generation story response "
                                   "and force tables through existing gateway if absent",
            prerequisites=("H04", "H05", "H06"),
        ),
        RecoveryItem(
            "H08", Lane.FUTURE_GATEWAY_IF_EXPORT_ABSENT,
            "A18_PHYSICAL_END_TOPOLOGY_NOT_QUALIFIED",
            (COORD, CUT), "Two old Global points and original section data exist",
            "Distance 5150 mm does not prove face-to-face free length, "
            "member releases, local axes, connected beam/column restraint or bottom/top",
            "Search current-or-equivalent A17/A18 topology/connection/release evidence; "
            "review concrete face offsets and panel-zone definitions",
            future_gateway_capture="Capture complete frame/node/section/local axis/"
                                   "end-release/adjacency facts with existing gateway if absent",
            prerequisites=("H02", "H04"),
        ),
        RecoveryItem(
            "H09", Lane.DERIVE_AFTER_PREREQUISITES,
            "A19_LN_K_UNPROVEN",
            (CUT, DECL, REC, COORD),
            "Archived reported ln=4450 mm, connectivity length=5150 mm",
            "Neither number is a source-authorized TS500 regulatory ln",
            "After H03/H07/H08, reuse original A19 TS500 kernel offline "
            "for physical ln, both-axis alpha, k and Lk",
            prerequisites=("H03", "H07", "H08"),
        ),
        RecoveryItem(
            "H10", Lane.DERIVE_AFTER_PREREQUISITES,
            "A20_DESIGN_MOMENT_LINEAGE_NOT_QUALIFIED",
            (REC, CUT),
            "Grav_Ult first-station native M3=-28.6274508388 kN·m but "
            "separate design M3=-171.5232 kN·m",
            "Separate design moment is not demonstrated as identical "
            "signed concurrent N-M2-M3 state",
            "After H05/H08, produce exact same-case native signed I/J M1/M2 "
            "and an independently verified design-force transformation",
            prerequisites=("H05", "H08"),
        ),
        RecoveryItem(
            "H11", Lane.FUTURE_GATEWAY_IF_EXPORT_ABSENT,
            "M6B_AND_SECOND_ORDER_OPEN",
            (CUT, READY, STAB),
            "Modal M6-B OPEN; global Delta not proven",
            "Response-spectrum extrema are not concurrent signed N/M2/M3, "
            "and old story force operands conflict",
            "Search full response-spectrum, mode/case combination and story-action "
            "records for a single verified current generation; otherwise later "
            "native source capture and engineering code review required",
            future_gateway_capture="Acquire M6-B compatible analysis/result "
                                   "evidence with existing gateway when authorized",
            prerequisites=("H04", "H05", "H07"),
        ),
        RecoveryItem(
            "H12", Lane.DERIVE_AFTER_PREREQUISITES,
            "FINAL_PMM_AND_COLUMN_CODE_CHECKS_BLOCKED",
            (CUT, READY),
            "Old snapshot has 38 empty authority fields; full design false",
            "Math tests alone cannot prove TS500/TBDY longitudinal, confinement, "
            "shear, joint, cage, all combinations and all stations",
            "Use same proven generation, the retained S1-D/S1-E and PMM "
            "kernels only after H03–H11 close with independent numeric checks",
            prerequisites=("H03", "H04", "H05", "H07", "H08", "H09",
                           "H10", "H11"),
        ),
    )
    ids = {x.id for x in items}
    if len(ids) != len(items) or any(
            any(dep not in ids for dep in row.prerequisites)
            for row in items):
        raise S1HError("INVALID_RECOVERY_DEPENDENCY_GRAPH")
    # Paths are discovery hints, never proof. No same-epoch claim is made even
    # if a file's name appears to contain A18, 235 or a known load case.
    known_archive = set(archive_members)
    program = tuple(sorted(p for p in SOURCE_PRODUCERS if p in known_archive))
    return S1HRecoveryPlan(
        schema="column.s1h.offline-source-routing.v1",
        component_id="235",
        status="SOURCE_RECOVERY_PLAN_PREPARED_CURRENT_DESIGN_BLOCKED",
        source_digest_sha256={key: PINNED[key] for key in sorted(PINNED)},
        original_235_frameforce_rows=prior.archived_frameforce_row_count,
        preserved_native_fact_count=len(native),
        archive_document_count=len(PINNED),
        candidate_model_sha256=model,
        recorded_model_sha256=recorded,
        source_models_rebound=False,
        full_project_design_proven=False,
        etabs_live_executed=False,
        items=items,
        offline_search_inventory=program,
        future_capture_order=("H04", "H05", "H07", "H08", "H11"),
        release_blockers=(
            "CURRENT_MODEL_ANALYSIS_GENERATION",
            "B5_B6_FULL_STATIC_AND_MODAL_CENSUS",
            "PROJECT_REVIEWED_GEOMETRY",
            "A17_STORY_STABILITY",
            "A18_CURRENT_PHYSICAL_ENDS_AND_LOCAL_AXES",
            "A19_FREE_LENGTH_AND_EFFECTIVE_LENGTH",
            "A20_SIGNED_END_AND_DESIGN_MOMENT_LINEAGE",
            "M6B_SEISMIC_AND_SECOND_ORDER",
            "FINAL_ALL_STATION_PMM_AND_RC_CODE_CHECKS",
        ),
    )


def plan_from_archive_zip(source_zip: str | Path) -> S1HRecoveryPlan:
    path = Path(source_zip)
    with ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise S1HError("DUPLICATE_ZIP_MEMBER_NAMES")
        # Read only fixed, known, capped JSON documents. Never unpack arbitrary
        # source files or execute anything stored in the archive.
        raw = {}
        for name in PINNED:
            if name not in names:
                raise S1HError(f"MISSING_PINNED_SOURCE:{name}")
            info = archive.getinfo(name)
            if info.file_size > 250_000:
                raise S1HError(f"PINNED_SOURCE_SIZE_LIMIT:{name}")
            raw[name] = archive.read(name)
        return derive_recovery_plan(raw, archive_members=tuple(names))
