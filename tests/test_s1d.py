
"""S1-D: legacy TS500 pure kernels + strict provisional mechanics composition."""
from dataclasses import replace
from math import pi
import unittest

from tbdy_column_core.contracts import DemandKind, EvidenceKey
from tbdy_column_core.physics.minimum_eccentricity import (
    ts500_minimum_eccentricity_mm, apply_ts500_minimum_eccentricity,
)
from tbdy_column_core.physics.moment_magnification import (
    ColumnMomentMagnificationAxisBasis, STIFFNESS_METHOD_EQ_7_21,
    evaluate_ts500_axis_moment_magnification,
)
from tbdy_column_core.physics.slenderness import (
    ColumnSlendernessAxisBasis, ColumnSlendernessBasis,
    SWAY_PREVENTED, evaluate_ts500_column_slenderness,
)
from tbdy_column_core.physics.rebar_selection import ColumnDemandState
from tbdy_column_core.physics.section_capacity import ColumnSectionMaterial
from tbdy_column_core.s1 import (
    DemandReadiness, DemandStationKey, QualifiedColumnDemand,
    S1ColumnSnapshot, SourceClass,
)
from tbdy_column_core.s1d_mechanics import (
    S1DMagnificationPair, S1DStatus, preview_ts500_static_mechanics,
)

E = EvidenceKey("a" * 64, "synthetic-epoch", "synthetic-gen",
                "synthetic-set", DemandKind.SIGNED_LINEAR_STATIC)
I_MOMENT = 400**4 / 12


def demand(station, *, nd=500_000, m2=1_000_000, m3=-2_000_000, end=None):
    if end is None:
        end = "I_END" if station == 0 else "J_END" if station == 3000 else "INTERIOR"
    return QualifiedColumnDemand(
        state_id=f"LC1|E1|{station}", column_id="C1", output_case="LC1",
        end_tag=end, nd_compression_n=nd, m2_nmm=m2, m3_nmm=m3,
        evidence=replace(E, case_state_id="LC1"),
        station_mm=station, element_id="E1", element_station_mm=station,
        step_type="Single Value", step_number=0,
    )


def snap(*, nd=500_000, source=SourceClass.SYNTHETIC_VALIDATION,
         readiness=DemandReadiness.RAW_FIRST_ORDER, m2=1_000_000, m3=-2_000_000):
    stations = (0, 1500, 3000)
    return S1ColumnSnapshot(
        column_id="C1", evidence=E, source_class=source,
        demand_readiness=readiness, basis_refs=(),
        width_mm=400, depth_mm=400, clear_cover_mm=40, tie_diameter_mm=8,
        aggregate_max_mm=20, allowed_bar_diameters_mm=(20,),
        material=ColumnSectionMaterial(35, 35 / 1.5, 500 / 1.15),
        demands=tuple(demand(s, nd=nd, m2=m2, m3=m3) for s in stations),
        expected_case_ids=("LC1",),
        expected_station_keys=tuple(DemandStationKey("LC1", "E1", s, s)
                                    for s in stations),
    )


def slenderness_basis(free=1500, *, ratio=0.0):
    def axis(name):
        return ColumnSlendernessAxisBasis(
            axis=name, section_dimension_mm=400,
            free_length_ln_mm=free, effective_length_factor_k=1.0,
            sway_classification=SWAY_PREVENTED, moment_ratio_m1_over_m2=ratio,
            source_refs=(f"SYN:{name}:physical-free-length-reviewed",),
        )
    return ColumnSlendernessBasis(
        component_id="C1", m2=axis("M2"), m3=axis("M3"),
        source_refs=("SYN:source-provided-basis",),
    )


def magnification_bases(snapshot, *, free=5000, nd_offset=0):
    def basis(state, axis):
        return ColumnMomentMagnificationAxisBasis(
            demand_state_id=state.state_id, axis=axis,
            sway_classification=SWAY_PREVENTED,
            nd_compression_n=state.nd_compression_n + nd_offset,
            m1_over_m2=None,
            horizontal_load_between_ends=True,
            effective_length_lk_mm=free, radius_i_mm=120,
            ec_mpa=34_000, ic_mm4=I_MOMENT, creep_ratio_rm=0.25,
            stiffness_method=STIFFNESS_METHOD_EQ_7_21,
            source_refs=(f"SYN:{state.state_id}:{axis}:EI-reviewed",),
        )
    return tuple(S1DMagnificationPair(d.state_id,
                                      m2=basis(d,"M2"),m3=basis(d,"M3"))
                 for d in snapshot.demands)


class RetainedPhysicsCalculations(unittest.TestCase):
    def test_ts500_independent_minimum_eccentricity_numbers(self):
        self.assertEqual(ts500_minimum_eccentricity_mm(400), 27.0)
        self.assertEqual(ts500_minimum_eccentricity_mm(800), 39.0)
        self.assertEqual(500_000 * ts500_minimum_eccentricity_mm(400), 13_500_000)

    def test_zero_moment_branches_both_signs(self):
        state = ColumnDemandState(
            "s1", "C1", "LC1", "SIGNED_LINEAR_STATIC", None, None,
            0.0, "I_END", 500_000, 0, 0, "SYN:one",
        )
        result = apply_ts500_minimum_eccentricity(
            component_id="C1", width_mm=400, depth_mm=400,
            demands=(state,),
        )
        self.assertEqual(result.output_state_count, 4)
        self.assertEqual({round(x.m2_nmm) for x in result.states},
                         {-13_500_000, 13_500_000})
        self.assertEqual({round(x.m3_nmm) for x in result.states},
                         {-13_500_000, 13_500_000})

    def test_slenderness_50_over_i_120_requires_magnification(self):
        r = evaluate_ts500_column_slenderness(
            component_id="C1", basis=slenderness_basis(free=6000))
        self.assertEqual(r.status, "REQUIRES_MOMENT_MAGNIFICATION")
        self.assertAlmostEqual(r.m2.slenderness_ratio_lk_over_i, 50)

    def test_independent_magnification_ei_nk_beta_arithmetic(self):
        s = snap()
        basis = magnification_bases(s)[0].m2
        r = evaluate_ts500_axis_moment_magnification(basis)
        expected_ei = (0.4 * 34_000 * I_MOMENT) / 1.25
        expected_nk = pi**2 * expected_ei / 5000**2
        expected_beta = 1.0 / (1.0 - 500_000 / (1.3 * expected_nk))
        self.assertAlmostEqual(r.effective_ei_nmm2, expected_ei, delta=1)
        self.assertAlmostEqual(r.critical_load_nk_n, expected_nk, delta=1)
        self.assertAlmostEqual(r.final_magnification_factor, expected_beta, places=10)
        self.assertGreater(r.final_magnification_factor, 1.0)


class MechanicsPreviewTests(unittest.TestCase):
    def test_low_slenderness_min_e_at_ends_only_middle_original(self):
        result = preview_ts500_static_mechanics(snap(),
                                                slenderness=slenderness_basis())
        self.assertEqual(result.status, S1DStatus.NUMERIC_MECHANICS_PREVIEW_NOT_FINAL)
        self.assertFalse(result.final_design_demand_proven)
        self.assertEqual(result.input_state_count, 3)
        self.assertEqual(result.output_state_count, 3)
        self.assertEqual(result.intermediate_station_count, 1)
        self.assertEqual(result.adjusted_end_state_count, 2)
        self.assertEqual(result.axis_magnification_count, 0)
        interior = [s for s in result.derived_states if s.end_tag=="INTERIOR"]
        self.assertEqual(len(interior), 1)
        self.assertEqual(interior[0].m2_nmm, 1_000_000)
        ends = [s for s in result.derived_states if s.end_tag in ("I_END","J_END")]
        self.assertEqual(len(ends),2)
        self.assertTrue(all(s.m2_nmm == 13_500_000 for s in ends))
        self.assertTrue(all(s.m3_nmm == -13_500_000 for s in ends))

    def test_magnification_only_when_slenderness_requires_it(self):
        s = snap()
        r = preview_ts500_static_mechanics(
            s, slenderness=slenderness_basis(free=5000),
            magnification=magnification_bases(s),
        )
        self.assertEqual(r.status, S1DStatus.NUMERIC_MECHANICS_PREVIEW_NOT_FINAL)
        self.assertEqual(r.axis_magnification_count, 6)
        self.assertEqual(r.intermediate_station_count, 1)
        interior = next(d for d in r.derived_states if d.end_tag=="INTERIOR")
        self.assertGreater(interior.m2_nmm, 1_000_000)
        self.assertLess(interior.m3_nmm, -2_000_000)

    def test_missing_slenderness_is_not_assumed(self):
        r = preview_ts500_static_mechanics(snap(), slenderness=None)
        self.assertEqual(r.status, S1DStatus.MECHANICS_BASIS_BLOCKED)
        self.assertFalse(r.derived_states)

    def test_needed_magnification_cannot_be_omitted(self):
        r = preview_ts500_static_mechanics(snap(),
                                           slenderness=slenderness_basis(free=5000))
        self.assertEqual(r.status, S1DStatus.MAGNIFICATION_BASIS_BLOCKED)

    def test_one_missing_state_factor_is_blocked(self):
        s = snap()
        bases = magnification_bases(s)
        r = preview_ts500_static_mechanics(
            s, slenderness=slenderness_basis(free=5000),
            magnification=bases[:2])
        self.assertEqual(r.status, S1DStatus.MAGNIFICATION_BASIS_BLOCKED)

    def test_wrong_nd_in_magnification_is_blocked(self):
        s = snap()
        r = preview_ts500_static_mechanics(
            s, slenderness=slenderness_basis(free=5000),
            magnification=magnification_bases(s,nd_offset=1000))
        self.assertEqual(r.status, S1DStatus.MAGNIFICATION_BASIS_BLOCKED)

    def test_high_slenderness_requires_general_analysis(self):
        r = preview_ts500_static_mechanics(
            snap(), slenderness=slenderness_basis(free=13000))
        self.assertEqual(r.status, S1DStatus.GENERAL_ANALYSIS_REQUIRED)

    def test_recorded_etabs_is_not_promoted_by_hand_written_basis(self):
        s = snap(source=SourceClass.RECORDED_ETABS)
        r = preview_ts500_static_mechanics(
            s, slenderness=slenderness_basis(free=1500))
        self.assertEqual(r.status, S1DStatus.EVIDENCE_BLOCKED)

    def test_final_reviewed_flag_blocks_double_second_order(self):
        s = snap(readiness=DemandReadiness.FINAL_DESIGN_REVIEWED)
        r = preview_ts500_static_mechanics(
            s, slenderness=slenderness_basis(free=5000),
            magnification=magnification_bases(s))
        self.assertEqual(r.status, S1DStatus.EVIDENCE_BLOCKED)

    def test_unqualified_physical_end_tag_blocks_minimum_eccentricity(self):
        s = snap()
        s = replace(s, demands=tuple(replace(d,end_tag="STATION") for d in s.demands))
        r = preview_ts500_static_mechanics(s, slenderness=slenderness_basis())
        self.assertEqual(r.status, S1DStatus.EVIDENCE_BLOCKED)

    def test_stale_magnification_not_reused_in_nonslender_state(self):
        s = snap()
        r = preview_ts500_static_mechanics(s, slenderness=slenderness_basis(),
                                           magnification=magnification_bases(s))
        self.assertEqual(r.status, S1DStatus.MAGNIFICATION_BASIS_BLOCKED)


if __name__ == "__main__":
    unittest.main()
