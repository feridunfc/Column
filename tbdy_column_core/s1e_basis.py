"""S1-E: small, offline A18/A19/A20 -> A21/A22 *basis producer*.

Original TS500 numerical owners are reused. Provenance is checked on every
boundary. Qualified recorded ETABS facts are NOT yet available in this repo;
the product path remains blocked rather than accepting synthetic review labels.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isclose, isfinite

from .contracts import DemandKind, EvidenceKey
from .s1 import S1ColumnSnapshot, SourceClass, DemandReadiness
from .physics.rebar_selection import ColumnDemandState
from .physics.effective_length import (
    EndRestraintMemberContribution, ColumnEffectiveLengthAxisBasis,
    evaluate_ts500_end_restraint_ratio,
    evaluate_ts500_effective_length_factor, column_effective_length_mm,
)
from .physics.end_moment_ratio import (
    ColumnEndMomentRatioEvidence, build_exact_static_end_moment_ratio,
)
from .physics.slenderness import (
    SWAY_PREVENTED, ColumnSlendernessAxisBasis, ColumnSlendernessBasis,
    evaluate_ts500_column_slenderness, MOMENT_MAGNIFICATION_REQUIRED,
    GENERAL_SECOND_ORDER_ANALYSIS_REQUIRED,
    SIGNED_END_MOMENT_RATIO_REQUIRED_FOR_SLENDERNESS_DECISION,
)
from .physics.moment_magnification import (
    STIFFNESS_METHOD_EQ_7_21, ColumnMomentMagnificationAxisBasis,
)
from .s1d_mechanics import S1DMagnificationPair


class S1EBasisStatus(StrEnum):
    SOURCE_BLOCKED = "SOURCE_BLOCKED"
    MISSING_PHYSICAL_TOPOLOGY = "MISSING_PHYSICAL_TOPOLOGY"
    MISSING_STORY_SWAY = "MISSING_STORY_SWAY"
    UNSUPPORTED_SWAY_NEEDS_STORY_AGGREGATES = "UNSUPPORTED_SWAY_NEEDS_STORY_AGGREGATES"
    MISSING_REQUIRED_MECHANICS = "MISSING_REQUIRED_MECHANICS"
    READY_SYNTHETIC_BASIS_NOT_REAL_RELEASE = "READY_SYNTHETIC_BASIS_NOT_REAL_RELEASE"


@dataclass(frozen=True, slots=True)
class S1EAxisFacts:
    """Input of existing A17/A18/A19 A22 *producers*, not UI user numbers.

    Source/epoch ID must be acquired by a source-verified provider. An ordinary
    nonempty ref or a truthy source flag is not itself such verification.
    """
    axis: str
    evidence: EvidenceKey
    bottom_columns: tuple[EndRestraintMemberContribution, ...]
    bottom_beams: tuple[EndRestraintMemberContribution, ...]
    top_columns: tuple[EndRestraintMemberContribution, ...]
    top_beams: tuple[EndRestraintMemberContribution, ...]
    free_length_ln_mm: float | None
    free_length_producer_ref: str | None
    sway_classification: str | None
    sway_producer_ref: str | None
    physical_end_topology_ref: str | None
    one_end_hinged: bool | None
    horizontal_load_between_ends: bool | None
    ec_mpa: float | None
    ic_mm4: float | None
    creep_ratio_rm: float | None
    mechanics_source_ref: str | None

    def __post_init__(self) -> None:
        if self.axis not in ("M2", "M3"):
            raise ValueError("INVALID_LOCAL_AXIS")
        if self.free_length_ln_mm is not None and (
            not isfinite(self.free_length_ln_mm) or self.free_length_ln_mm <= 0
        ):
            raise ValueError("INVALID_REGULATORY_FREE_LENGTH")
        if self.one_end_hinged is not None and type(self.one_end_hinged) is not bool:
            raise ValueError("INVALID_END_HINGE_TYPE")
        if self.horizontal_load_between_ends is not None and type(
            self.horizontal_load_between_ends
        ) is not bool:
            raise ValueError("HORIZONTAL_LOAD_FACT_MUST_BE_EXPLICIT_BOOL")


@dataclass(frozen=True, slots=True)
class S1EAxisResult:
    axis: str
    alpha_bottom: float
    alpha_top: float
    k: float
    ln_mm: float
    lk_mm: float
    sway_classification: str
    source_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class S1ECaseBasis:
    output_case: str
    end_moment_ratios: tuple[ColumnEndMomentRatioEvidence, ...]
    slenderness_basis: ColumnSlendernessBasis
    slenderness_status: str
    magnification_pairs: tuple[S1DMagnificationPair, ...]


@dataclass(frozen=True, slots=True)
class S1EBasisResult:
    column_id: str
    status: S1EBasisStatus
    reason: str
    axes: tuple[S1EAxisResult, ...] = ()
    cases: tuple[S1ECaseBasis, ...] = ()
    automatic_numeric_basis_available: bool = False
    real_etabs_basis_qualified: bool = False


def _blocked(s: S1ColumnSnapshot, status: S1EBasisStatus, reason: str):
    return S1EBasisResult(column_id=s.column_id, status=status, reason=reason)


def _same_evidence(actual: EvidenceKey, expected: EvidenceKey) -> bool:
    return (actual.model_sha256, actual.epoch_id,
            actual.analysis_generation, actual.kind, actual.unit_system) == (
                expected.model_sha256, expected.epoch_id,
                expected.analysis_generation, expected.kind, expected.unit_system)


def _end_state(snapshot: S1ColumnSnapshot, case: str, tag: str) -> ColumnDemandState:
    rows = [d for d in snapshot.demands
            if d.output_case == case and d.end_tag == tag]
    if len(rows) != 1:
        raise ValueError(f"EXPECTED_EXACTLY_ONE_PHYSICAL_{tag}_FOR_{case}")
    d = rows[0]
    if d.element_id is None or d.station_mm is None:
        raise ValueError("PHYSICAL_END_MUST_CARRY_ELEMENT_AND_STATION")
    if d.step_type not in (None, "Single Value"):
        raise ValueError("NON_SIMULTANEOUS_END")
    return ColumnDemandState(
        state_id=d.state_id, component_id=snapshot.column_id,
        output_case=case, case_type="DesignStaticLinearExact",
        step_type=None, step_number=None,
        station_m=d.station_mm / 1000, end_tag=tag,
        nd_compression_n=d.nd_compression_n,
        m2_nmm=d.m2_nmm, m3_nmm=d.m3_nmm,
        source_identity=(
            f"{d.evidence.model_sha256}|{d.evidence.epoch_id}|"
            f"{d.evidence.analysis_generation}|{case}|{d.element_id}|"
            f"{d.station_mm}|{d.state_id}"
        ),
    )


def prepare_s1e_basis(
    snapshot: S1ColumnSnapshot,
    *,
    axis_facts: tuple[S1EAxisFacts, ...],
) -> S1EBasisResult:
    """Derive ratios, k, Lk, slenderness and axis EI/Nk *basis*, synthetically.

    A result here can never authorize a recorded ETABS PMM; its source values
    need the original A17/A18/free-length/analysis producer chain.
    """
    if snapshot.source_class is not SourceClass.SYNTHETIC_VALIDATION:
        return _blocked(snapshot, S1EBasisStatus.SOURCE_BLOCKED,
                        "NATIVE_A17_A18_A19_A20_SOURCE_BINDING_NOT_AVAILABLE")
    if snapshot.demand_readiness is not DemandReadiness.RAW_FIRST_ORDER:
        return _blocked(snapshot, S1EBasisStatus.SOURCE_BLOCKED,
                        "PRODUCER_ACCEPTS_ONLY_RAW_FIRST_ORDER_TO_AVOID_DUPLICATE_EFFECTS")
    if snapshot.evidence.kind != DemandKind.SIGNED_LINEAR_STATIC:
        return _blocked(snapshot, S1EBasisStatus.SOURCE_BLOCKED,
                        "MODAL_OR_ENVELOPE_NOT_SUPPORTED")
    if (len(axis_facts) != 2 or
        {r.axis for r in axis_facts} != {"M2", "M3"} or
        any(not _same_evidence(r.evidence, snapshot.evidence) for r in axis_facts)):
        return _blocked(snapshot, S1EBasisStatus.SOURCE_BLOCKED,
                        "AXIS_IDENTITY_OR_MODEL_GENERATION_MISMATCH")
    if any(
        not r.physical_end_topology_ref or
        not r.free_length_producer_ref or r.free_length_ln_mm is None or
        r.one_end_hinged is None or
        not r.sway_producer_ref or r.sway_classification is None
        for r in axis_facts
    ):
        return _blocked(snapshot, S1EBasisStatus.MISSING_PHYSICAL_TOPOLOGY,
                        "A17_A18_FREE_LENGTH_AND_END_CONNECTIONS_REQUIRED")
    if any(r.sway_classification != SWAY_PREVENTED for r in axis_facts):
        return _blocked(snapshot,
                        S1EBasisStatus.UNSUPPORTED_SWAY_NEEDS_STORY_AGGREGATES,
                        "SWAY_PERMITTED_REQUIRES_FULL_STORY_SUM_ND_SUM_NK_AND_M6_B")
    if any(
        r.ec_mpa is None or r.ic_mm4 is None or
        r.creep_ratio_rm is None or not r.mechanics_source_ref or
        r.horizontal_load_between_ends is None
        for r in axis_facts
    ):
        return _blocked(snapshot, S1EBasisStatus.MISSING_REQUIRED_MECHANICS,
                        "REQUIRE_SOURCE_BOUND_EC_IC_CREEP_AND_HORIZONTAL_LOAD")
    results: dict[str, S1EAxisResult] = {}
    try:
        for r in axis_facts:
            bottom = evaluate_ts500_end_restraint_ratio(
                end_tag="BOTTOM", axis=r.axis,
                column_contributions=r.bottom_columns,
                beam_contributions=r.bottom_beams,
                source_refs=(r.physical_end_topology_ref,),
            )
            top = evaluate_ts500_end_restraint_ratio(
                end_tag="TOP", axis=r.axis,
                column_contributions=r.top_columns,
                beam_contributions=r.top_beams,
                source_refs=(r.physical_end_topology_ref,),
            )
            fact = ColumnEffectiveLengthAxisBasis(
                axis=r.axis, sway_classification=r.sway_classification,
                alpha_bottom=bottom.alpha, alpha_top=top.alpha,
                one_end_hinged=r.one_end_hinged,
                source_refs=tuple(dict.fromkeys((
                    *bottom.source_refs, *top.source_refs,
                    r.sway_producer_ref, r.free_length_producer_ref,
                ))),
            )
            k = evaluate_ts500_effective_length_factor(fact)
            ln = float(r.free_length_ln_mm)
            lk = column_effective_length_mm(free_length_mm=ln, factor=k)
            results[r.axis] = S1EAxisResult(
                axis=r.axis, alpha_bottom=bottom.alpha,
                alpha_top=top.alpha, k=k.effective_length_factor_k,
                ln_mm=ln, lk_mm=lk,
                sway_classification=r.sway_classification,
                source_refs=k.source_refs,
            )
        cases: list[S1ECaseBasis] = []
        for case in snapshot.expected_case_ids:
            I, J = _end_state(snapshot, case, "I_END"), _end_state(
                snapshot, case, "J_END"
            )
            if (I.source_identity.split("|")[:3] !=
                J.source_identity.split("|")[:3]):
                raise ValueError("ENDS_NOT_FROM_SAME_ANALYSIS_GENERATION")
            # A constant axial force is NOT a TS500 requirement for end
            # moment ratios. Gravity loads and distributed member weight
            # legitimately produce different I/J axial forces. Each station
            # retains its own Nd in its individual magnification basis below.
            # This routine does NOT derive a global buckling/stability Nd.
            ratios = tuple(
                build_exact_static_end_moment_ratio(
                    i_end=I, j_end=J, axis=axis,
                    analysis_result_ref=f"SYNTHETIC_STATIC:{case}",
                    source_refs=(f"SYNTHETIC_SOURCE:{case}",
                                 results[axis].source_refs[0]),
                )
                for axis in ("M2", "M3")
            )
            basis_by_axis = {
                axis: ColumnSlendernessAxisBasis(
                    axis=axis,
                    section_dimension_mm=(snapshot.depth_mm
                                          if axis == "M2" else snapshot.width_mm),
                    free_length_ln_mm=results[axis].ln_mm,
                    effective_length_factor_k=results[axis].k,
                    sway_classification=results[axis].sway_classification,
                    moment_ratio_m1_over_m2=(
                        next(e for e in ratios if e.axis == axis).
                        moment_ratio_m1_over_m2
                    ),
                    source_refs=results[axis].source_refs,
                )
                for axis in ("M2", "M3")
            }
            slenderness_basis = ColumnSlendernessBasis(
                component_id=snapshot.column_id,
                m2=basis_by_axis["M2"], m3=basis_by_axis["M3"],
                source_refs=(f"S1E_SYNTHETIC_MECHANICS_CASE:{case}",),
            )
            evaluated = evaluate_ts500_column_slenderness(
                component_id=snapshot.column_id, basis=slenderness_basis
            )
            if evaluated.status == GENERAL_SECOND_ORDER_ANALYSIS_REQUIRED:
                raise ValueError("GENERAL_SECOND_ORDER_ANALYSIS_REQUIRED")
            if evaluated.status == SIGNED_END_MOMENT_RATIO_REQUIRED_FOR_SLENDERNESS_DECISION:
                raise ValueError("SIGNED_END_RATIO_UNAVAILABLE")
            factors: list[S1DMagnificationPair] = []
            for d in (x for x in snapshot.demands if x.output_case == case):
                pair = {}
                for axis in ("M2", "M3"):
                    status = (evaluated.m2 if axis == "M2" else
                              evaluated.m3).status
                    if status != MOMENT_MAGNIFICATION_REQUIRED:
                        pair[axis] = None
                        continue
                    r = next(v for v in axis_facts if v.axis == axis)
                    axis_result = results[axis]
                    nd = float(d.nd_compression_n)
                    if nd < 0:
                        raise ValueError("NEGATIVE_AXIAL_DEMAND_IN_MAGNIFICATION")
                    pair[axis] = ColumnMomentMagnificationAxisBasis(
                        demand_state_id=d.state_id, axis=axis,
                        sway_classification=r.sway_classification,
                        nd_compression_n=nd,
                        m1_over_m2=(
                            next(v for v in ratios if v.axis == axis).
                            moment_ratio_m1_over_m2
                        ),
                        effective_length_lk_mm=axis_result.lk_mm,
                        radius_i_mm=(evaluated.m2 if axis == "M2" else
                                     evaluated.m3).radius_of_gyration_i_mm,
                        ec_mpa=r.ec_mpa, ic_mm4=r.ic_mm4,
                        creep_ratio_rm=r.creep_ratio_rm,
                        stiffness_method=STIFFNESS_METHOD_EQ_7_21,
                        horizontal_load_between_ends=r.horizontal_load_between_ends,
                        source_refs=(r.mechanics_source_ref,
                                     *axis_result.source_refs),
                    )
                if pair["M2"] is not None or pair["M3"] is not None:
                    factors.append(S1DMagnificationPair(
                        state_id=d.state_id, m2=pair["M2"], m3=pair["M3"],
                    ))
            cases.append(S1ECaseBasis(
                output_case=case, end_moment_ratios=ratios,
                slenderness_basis=slenderness_basis,
                slenderness_status=evaluated.status,
                magnification_pairs=tuple(factors),
            ))
    except (TypeError, ValueError, ArithmeticError) as exc:
        return _blocked(snapshot, S1EBasisStatus.MISSING_REQUIRED_MECHANICS,
                        f"SOURCE_OR_MECHANICS_ERROR:{exc}")
    return S1EBasisResult(
        column_id=snapshot.column_id,
        status=S1EBasisStatus.READY_SYNTHETIC_BASIS_NOT_REAL_RELEASE,
        reason="NUMERIC_BASIS_PREPARED_FROM_TYPED_SYNTHETIC_UPSTREAM_FACTS",
        axes=tuple(results[a] for a in ("M2", "M3")),
        cases=tuple(cases),
        automatic_numeric_basis_available=True,
        real_etabs_basis_qualified=False,
    )
