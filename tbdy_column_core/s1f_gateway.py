"""S1-F read-only consumer of the EXISTING etabs_gateway replay + TBDY A18/A19/A20.

The caller supplies the original etabs_gateway.replay.FixtureReplayProvider
and the original A18/A19/A20 materialization objects. No COM, ETABS import,
new gateway or dynamic load-state guess occurs. This module only reconciles
already-recorded objects; context SHA does NOT prove EDB/model/generation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isclose, isfinite
from typing import Any, Sequence

from .s1 import S1ColumnSnapshot
from .physics.effective_length import (
    ColumnEffectiveLengthAxisBasis,
    column_effective_length_mm, evaluate_ts500_effective_length_factor,
)
from .physics.end_moment_ratio import build_exact_static_end_moment_ratio
from .physics.rebar_selection import ColumnDemandState


A18_AUTHORITY = "COLUMN_R1_A18_TS500_END_RESTRAINT_FACTUAL_MATERIALIZATION"
A19_AUTHORITY = "COLUMN_R1_A19_TS500_EFFECTIVE_LENGTH_COMPOSITION"
A20_AUTHORITY = "COLUMN_R1_A20_EXACT_STATIC_END_MOMENT_COMPOSITION"


class S1FStatus(StrEnum):
    REPLAY_RECONCILED_NO_LIVE_PROOF = "REPLAY_RECONCILED_NO_LIVE_PROOF"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class ReplayedAxis:
    axis: str
    alpha_bottom: float
    alpha_top: float
    k: float
    ln_mm: float
    lk_mm: float
    sway: str


@dataclass(frozen=True, slots=True)
class ReplayedEndMoment:
    case: str
    axis: str
    ratio: float
    i_state_id: str
    j_state_id: str


@dataclass(frozen=True, slots=True)
class S1FGatewayResult:
    column_id: str
    status: S1FStatus
    reason: str
    gateway_context_fingerprint: str | None
    model_path_metadata: str | None
    axes: tuple[ReplayedAxis, ...] = ()
    end_moments: tuple[ReplayedEndMoment, ...] = ()
    analysis_generation_verified: bool = False
    edb_bytes_verified: bool = False
    real_design_basis_verified: bool = False


def _close(a: Any, b: Any) -> bool:
    try:
        x, y = float(a), float(b)
    except (ValueError, TypeError):
        return False
    return (isfinite(x) and isfinite(y)
            and isclose(x, y, rel_tol=1e-8, abs_tol=1e-7))


def _refs(record: Any) -> bool:
    v = getattr(record, "source_refs", None)
    return (isinstance(v, (tuple, list)) and bool(v)
            and all(isinstance(x, str) and x.strip() for x in v))


def _one(rows: Sequence[Any], axis: str, *, end: str | None = None,
         case: str | None = None) -> Any:
    candidates = [r for r in rows
                  if getattr(r, "local_bending_axis", None) == axis
                  and (end is None or getattr(r, "end_tag", None) == end)
                  and (case is None or getattr(r, "output_case", None) == case)]
    if len(candidates) != 1:
        raise ValueError(f"EXPECTED_EXACTLY_ONE_A18_A19_A20:{axis}:{end}:{case}")
    return candidates[0]


def _end(snapshot: S1ColumnSnapshot, case: str, tag: str) -> ColumnDemandState:
    found = [r for r in snapshot.demands
             if r.output_case == case and r.end_tag == tag]
    if len(found) != 1:
        raise ValueError(f"PHYSICAL_{tag}_NOT_QUALIFIED:{case}")
    d = found[0]
    if (d.element_id is None or d.station_mm is None
            or d.step_type not in (None, "Single Value")
            or d.evidence.case_state_id != case):
        raise ValueError("EXACT_SIGNED_STATIC_END_PROVENANCE_REQUIRED")
    return ColumnDemandState(
        state_id=d.state_id,
        component_id=d.column_id, output_case=case,
        case_type="DesignStaticLinearExact", step_type=None,
        step_number=None, station_m=d.station_mm / 1000.0,
        end_tag=tag, nd_compression_n=d.nd_compression_n,
        m2_nmm=d.m2_nmm, m3_nmm=d.m3_nmm,
        source_identity=(f"{d.evidence.model_sha256}|{d.evidence.epoch_id}|"
                         f"{d.evidence.analysis_generation}|{case}|"
                         f"{d.element_id}|{d.station_mm}|{d.state_id}"),
    )


def reconcile_existing_gateway_replay(
    replay_provider: Any,
    snapshot: S1ColumnSnapshot,
    *,
    a18_rows: Sequence[Any],
    a19_rows: Sequence[Any],
    a20_rows: Sequence[Any],
) -> S1FGatewayResult:
    """Use existing gateway FixtureReplayProvider and old typed materializations.

    The gateway provider is injected, not replaced. Replaying an old context
    may validate its own SHA-256 but cannot prove model bytes, analysis run,
    load-combination coverage or originating ETABS identity. These remain false.
    """
    base = dict(column_id=snapshot.column_id,
                gateway_context_fingerprint=None, model_path_metadata=None)

    def blocked(reason: str, *, fingerprint=None, model_path=None):
        return S1FGatewayResult(
            column_id=snapshot.column_id, status=S1FStatus.BLOCKED,
            reason=reason, gateway_context_fingerprint=fingerprint,
            model_path_metadata=model_path,
        )

    try:
        # These members are public on ORIGINAL etabs_gateway.replay provider.
        fixture = replay_provider.fixture
        if fixture.schema_version != "1.0" or fixture.fixture_type != "ETABS_GATEWAY_CONTEXT":
            raise ValueError("EXISTING_GATEWAY_FIXTURE_CONTRACT_MISMATCH")
        fingerprint = fixture.sha256
        if (not isinstance(fingerprint, str) or len(fingerprint) != 64
                or any(c not in "0123456789abcdef" for c in fingerprint)
                or replay_provider.fingerprint != fingerprint):
            raise ValueError("EXISTING_GATEWAY_FINGERPRINT_MISMATCH")
        context = replay_provider.read_context()
        if context is not fixture.context:
            raise ValueError("REPLAY_PROVIDER_RETURNED_DIFFERENT_CONTEXT_OBJECT")
        model = context.model
        model_path = model.model_path
        if not model.has_open_model or not isinstance(model_path, str) or not model_path:
            raise ValueError("GATEWAY_CONTEXT_HAS_NO_MODEL_METADATA")
        if model.units is None:
            raise ValueError("GATEWAY_CONTEXT_MISSING_UNIT_METADATA")

        if (len(a18_rows) != 4 or len(a19_rows) != 2
                or len(a20_rows) != 2 * len(snapshot.expected_case_ids)):
            raise ValueError("INCOMPLETE_MATERIALIZATION_POPULATION")
        if snapshot.evidence.kind.value != "SIGNED_LINEAR_STATIC":
            raise ValueError("UNSUPPORTED_NONSTATIC_EVIDENCE")
        axes = []
        for axis in ("M2", "M3"):
            bottoms = _one(a18_rows, axis, end="BOTTOM")
            tops = _one(a18_rows, axis, end="TOP")
            a19 = _one(a19_rows, axis)
            for obj, authority in (
                (bottoms, A18_AUTHORITY), (tops, A18_AUTHORITY),
                (a19, A19_AUTHORITY),
            ):
                if (getattr(obj, "authority", None) != authority
                        or getattr(obj, "disposition", None) != "READY"
                        or getattr(obj, "component_id", None) != snapshot.column_id
                        or not _refs(obj)):
                    raise ValueError("UNQUALIFIED_A18_A19_MATERIALIZATION")
            for end in (bottoms, tops):
                num = getattr(end, "numerator_column_i_over_l_m3", None)
                den = getattr(end, "denominator_beam_i_over_l_m3", None)
                if (not _close(num, num) or not _close(den, den)
                        or float(num) <= 0 or float(den) <= 0
                        or not _close(end.alpha, float(num) / float(den))):
                    raise ValueError("A18_ALPHA_NOT_RECONCILED_TO_I_OVER_L")
            if (not _close(a19.alpha_bottom, bottoms.alpha)
                    or not _close(a19.alpha_top, tops.alpha)):
                raise ValueError("A19_ALPHA_DISAGREES_WITH_A18")
            basis = ColumnEffectiveLengthAxisBasis(
                axis=axis, sway_classification=a19.sway_classification,
                alpha_bottom=bottoms.alpha, alpha_top=tops.alpha,
                one_end_hinged=a19.one_end_hinged,
                source_refs=tuple(a19.source_refs),
            )
            calc = evaluate_ts500_effective_length_factor(basis)
            lk = column_effective_length_mm(
                free_length_mm=a19.free_length_ln_mm, factor=calc
            )
            if (not _close(calc.effective_length_factor_k, a19.k)
                    or not _close(lk, a19.effective_length_lk_mm)):
                raise ValueError("A19_K_OR_LK_DISAGREES_WITH_ORIGINAL_TS500_KERNEL")
            axes.append(ReplayedAxis(
                axis=axis, alpha_bottom=bottoms.alpha, alpha_top=tops.alpha,
                k=a19.k, ln_mm=a19.free_length_ln_mm,
                lk_mm=a19.effective_length_lk_mm,
                sway=a19.sway_classification,
            ))

        ratios = []
        for case in snapshot.expected_case_ids:
            i = _end(snapshot, case, "I_END")
            j = _end(snapshot, case, "J_END")
            for axis in ("M2", "M3"):
                row = _one(a20_rows, axis, case=case)
                evidence = getattr(row, "evidence", None)
                if (getattr(row, "disposition", None) != "READY"
                        or getattr(row, "authority", None) != A20_AUTHORITY
                        or getattr(row, "component_id", None) != snapshot.column_id
                        or evidence is None or not _refs(row)
                        or not getattr(row, "analysis_result_ref", None)):
                    raise ValueError("UNQUALIFIED_A20_MATERIALIZATION")
                expected = build_exact_static_end_moment_ratio(
                    i_end=i, j_end=j, axis=axis,
                    analysis_result_ref=row.analysis_result_ref,
                    source_refs=tuple(row.source_refs),
                )
                if (evidence.i_end_state_id != expected.i_end_state_id
                        or evidence.j_end_state_id != expected.j_end_state_id
                        or evidence.axis != expected.axis
                        or evidence.output_case != case
                        or not _close(evidence.m1_nmm, expected.m1_nmm)
                        or not _close(evidence.m2_nmm, expected.m2_nmm)
                        or not _close(evidence.moment_ratio_m1_over_m2,
                                      expected.moment_ratio_m1_over_m2)
                        or evidence.curvature != expected.curvature):
                    raise ValueError("A20_SIGNED_END_MOMENT_DISAGREEMENT")
                ratios.append(ReplayedEndMoment(
                    case=case, axis=axis, ratio=evidence.moment_ratio_m1_over_m2,
                    i_state_id=evidence.i_end_state_id,
                    j_state_id=evidence.j_end_state_id,
                ))
        return S1FGatewayResult(
            column_id=snapshot.column_id,
            status=S1FStatus.REPLAY_RECONCILED_NO_LIVE_PROOF,
            reason="ORIGINAL_GATEWAY_REPLAY_A18_A19_A20_NUMERICALLY_RECONCILED_ONLY",
            gateway_context_fingerprint=fingerprint,
            model_path_metadata=model_path, axes=tuple(axes),
            end_moments=tuple(ratios),
        )
    except (AttributeError, TypeError, ValueError, ArithmeticError) as exc:
        return blocked(f"REPLAY_OR_MATERIALIZATION_BLOCKED:{exc}")
