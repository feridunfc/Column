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
