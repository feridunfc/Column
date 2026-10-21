"""Frozen independent reference values for TS500 7.24 and 7.27.

These golden values deliberately do NOT obtain expected beta from the
production kernel's denominator. That old mistake escaped 79 green tests.
The Turkish TS500 2000 text takes normative priority over the English
translation's discrepant Eq.7.27 rendering.
"""
from dataclasses import replace
from math import pi
import unittest

from tbdy_column_core.physics.moment_magnification import (
    ColumnMomentMagnificationAxisBasis,
    STIFFNESS_METHOD_EQ_7_21,
    STATUS_BLOCKED,
    evaluate_ts500_axis_moment_magnification,
)
from tbdy_column_core.physics.slenderness import SWAY_PERMITTED, SWAY_PREVENTED
from tbdy_column_core.s1d_mechanics import (
    preview_ts500_static_mechanics, S1DStatus,
)
from tests.test_s1d import snap, slenderness_basis, magnification_bases


def basic():
    return ColumnMomentMagnificationAxisBasis(
        demand_state_id="independent", axis="M2",
        sway_classification=SWAY_PREVENTED,
        nd_compression_n=500_000, m1_over_m2=None,
        horizontal_load_between_ends=True,
        effective_length_lk_mm=5000, radius_i_mm=120,
        ec_mpa=34_000, ic_mm4=400**4/12, creep_ratio_rm=.25,
        stiffness_method=STIFFNESS_METHOD_EQ_7_21,
        source_refs=("TS500_7_24_TRANSLATION_FROZEN_NUMERIC_ORACLE",),
    )


class TS500IndependentNumericalOracles(unittest.TestCase):
    def test_eq724_cm1_nd_over_nk_0p2_is_1p351351(self):
        b = basic()
        k = evaluate_ts500_axis_moment_magnification(b).critical_load_nk_n
        r = evaluate_ts500_axis_moment_magnification(
            replace(b, nd_compression_n=.2*k))
        self.assertAlmostEqual(r.final_magnification_factor,
                               1.3513513513513513, places=12)
        # Old code 1 - Nd/(1.3 Nk) gives 1.181818..., definitely wrong.
        self.assertNotAlmostEqual(r.final_magnification_factor,
                                  1.1818181818181819, places=6)

    def test_eq724_positive_denominator_failure_at_0p8_nk(self):
        b = basic()
        k = evaluate_ts500_axis_moment_magnification(b).critical_load_nk_n
        r = evaluate_ts500_axis_moment_magnification(
            replace(b, nd_compression_n=.8*k))
        self.assertEqual(r.status, STATUS_BLOCKED)
        self.assertIn("NONPOSITIVE_DENOMINATOR", r.blockers[0])

    def test_eq727_turkish_ts500_and_2015_journal_story_beta_2p185(self):
        b=basic()
        # Independent 2015 paper case: each column Nd = 833kN, Nk = 1997kN,
        # story two identical columns, story beta_s ~ 2.185.
        target_nk=1_997_000.0
        lk=12449.0
        rm=.196
        ec=30_000.0
        section_i=target_nk*lk**2*(1+rm)/(pi*pi*.4*ec)
        r=evaluate_ts500_axis_moment_magnification(
            replace(
                b, sway_classification=SWAY_PERMITTED,
                nd_compression_n=833_000,
                effective_length_lk_mm=lk, radius_i_mm=150,
                ec_mpa=ec, ic_mm4=section_i,
                creep_ratio_rm=rm,
                story_sum_nd_n=2*833_000,
                story_sum_nk_n=2*1_997_000,
                fck_mpa=30, concrete_area_mm2=300*500,
            )
        )
        self.assertAlmostEqual(r.beta_story, 2.184662509572257, places=9)
        self.assertAlmostEqual(r.critical_load_nk_n, target_nk, delta=.001)

    def test_eq725_cm_half_positive_end_ratio_independent_value(self):
        source = basic()
        nk = evaluate_ts500_axis_moment_magnification(source).critical_load_nk_n
        result = evaluate_ts500_axis_moment_magnification(replace(
            source, horizontal_load_between_ends=False,
            m1_over_m2=0.5, nd_compression_n=0.2 * nk,
        ))
        # TS500 7.25 Cm=0.6+0.4*(+0.5)=0.8.
        # TS500 7.24 denominator=1-1.3*0.2=0.74.
        self.assertAlmostEqual(result.cm, 0.8, places=12)
        self.assertAlmostEqual(result.beta_individual, 40.0/37.0, places=12)

    def test_eq725_double_curvature_cm_floor_and_horizontal_override(self):
        source=basic()
        low=evaluate_ts500_axis_moment_magnification(replace(
            source, horizontal_load_between_ends=False,
            m1_over_m2=-0.9,
        ))
        self.assertAlmostEqual(low.cm, 0.4, places=12)
        sideways=evaluate_ts500_axis_moment_magnification(replace(
            source, horizontal_load_between_ends=True,
            m1_over_m2=None,
        ))
        self.assertAlmostEqual(sideways.cm, 1.0, places=12)

    def test_eq729_uses_fck_not_fcd_in_sway_slenderness_threshold(self):
        source=basic()
        # Explicit check in the band where fck vs fcd changes the decision.
        # slenderness=10200/120=85; fck threshold=35/sqrt(800k/5.6MN)
        # ~=92.60, while substituting fcd=35/1.5 gives ~75.60.
        # TS500's Eq 7.29 explicitly writes fck.
        modified=replace(
            source, sway_classification=SWAY_PERMITTED,
            nd_compression_n=800_000,
            effective_length_lk_mm=10200, radius_i_mm=120,
            story_sum_nd_n=800_000, story_sum_nk_n=10_000_000,
            fck_mpa=35, concrete_area_mm2=160_000,
        )
        result=evaluate_ts500_axis_moment_magnification(modified)
        self.assertAlmostEqual(result.cm, 1.0, places=12)
        self.assertAlmostEqual(result.slenderness_lk_over_i, 85.0)
        self.assertFalse(result.eq729_product_required)
        self.assertAlmostEqual(
            result.final_magnification_factor,
            max(result.beta_individual, result.beta_story),
        )

    def test_minimum_eccentricity_precedes_second_order_for_end_branch(self):
        s=snap(m2=0,m3=0)
        b=magnification_bases(s)
        result=preview_ts500_static_mechanics(
            s, slenderness=slenderness_basis(free=5000),
            magnification=b,
        )
        self.assertEqual(result.status,S1DStatus.NUMERIC_MECHANICS_PREVIEW_NOT_FINAL)
        self.assertEqual(result.output_state_count,9) # 2 ends x four sign branches + interior
        ends=[row for row in result.derived_states if row.end_tag in ("I_END","J_END")]
        self.assertEqual(len(ends),8)
        beta=evaluate_ts500_axis_moment_magnification(b[0].m2).final_magnification_factor
        self.assertGreater(beta,1.0)
        self.assertTrue(all(abs(abs(row.m2_nmm)-13_500_000*beta)<.001
                            for row in ends))
        self.assertFalse(result.final_design_demand_proven)


if __name__=="__main__":
    unittest.main()
