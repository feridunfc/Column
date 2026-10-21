from dataclasses import replace
import math
import unittest

from tbdy_column_core.contracts import DemandKind, EvidenceKey
from tbdy_column_core.physics.rebar_layout import ColumnRebarGeometryInputs, build_rectangular_column_rebar_geometry_candidate
from tbdy_column_core.physics.section_capacity import (
    ColumnSectionMaterial, evaluate_rectangular_column_capacity_state,
    ts500_k1_for_fck_mpa,
)
from tbdy_column_core.s1 import (
    DemandReadiness, QualifiedColumnDemand, S1ColumnSnapshot, S1Status,
    SourceClass, evaluate_s1_column,
)
from tbdy_column_core.s1_report import s1_report_json, s1_report_sha256
from tests.independent.oracle import evaluate_state, OracleMaterial, OracleBar


ANCHOR = EvidenceKey('b'*64, 'E1', 'GEN-1', 'PROJECT_S1', DemandKind.SIGNED_LINEAR_STATIC)


def demand(case='LC1', end='I_END', *, n=500_000, m2=25_000_000, m3=20_000_000, gen='GEN-1'):
    evidence = replace(ANCHOR, case_state_id=case, analysis_generation=gen)
    return QualifiedColumnDemand(f'{case}:{end}', 'C1', case, end, n, m2, m3, evidence)


def snapshot(*, readiness=DemandReadiness.FINAL_DESIGN_REVIEWED, refs=('STATIC_DESIGN_SCOPE_A1',),
             cases=('LC1',), demand_rows=None):
    if demand_rows is None:
        demand_rows = tuple(demand(c, end) for c in cases for end in ('I_END', 'J_END'))
    return S1ColumnSnapshot(
        column_id='C1', evidence=ANCHOR, source_class=SourceClass.SYNTHETIC_VALIDATION,
        demand_readiness=readiness, basis_refs=refs,
        width_mm=400.0, depth_mm=400.0, clear_cover_mm=40.0, tie_diameter_mm=8.0,
        aggregate_max_mm=20.0, allowed_bar_diameters_mm=(20.0,),
        material=ColumnSectionMaterial(35.0, 35/1.5, 500/1.15),
        demands=demand_rows, expected_case_ids=cases,
    )


class S1Integration(unittest.TestCase):
    def test_synthetic_produces_numeric_candidate_without_code_pass(self):
        result = evaluate_s1_column(snapshot(), angle_count=32)
        self.assertEqual(result.status, S1Status.NUMERIC_CANDIDATE_FOUND_NOT_FULL_TBDY)
        self.assertEqual(result.selected_bar_count, 6)
        self.assertAlmostEqual(result.selected_area_mm2, 6*math.pi*20*20/4)
        self.assertLess(result.governing_utilization, 1)
        self.assertFalse(result.full_tbd_y_qualified)
        self.assertIn('"engineering_release_qualified":false', s1_report_json(result))
        self.assertEqual(s1_report_sha256(result), s1_report_sha256(result))

    def test_final_design_basis_is_not_inferred_from_raw_etabs_rows(self):
        result = evaluate_s1_column(snapshot(readiness=DemandReadiness.RAW_FIRST_ORDER),angle_count=32)
        self.assertEqual(result.status, S1Status.DEMAND_BASIS_BLOCKED)
        self.assertIsNone(result.governing_utilization)

    def test_missing_review_refs_blocks_numeric_selection(self):
        result = evaluate_s1_column(snapshot(refs=()),angle_count=32)
        self.assertEqual(result.status, S1Status.DEMAND_BASIS_BLOCKED)

    def test_two_load_cases_complete_and_select_governing_demand(self):
        result=evaluate_s1_column(snapshot(cases=('LC1','LC2'),demand_rows=(
            demand('LC1','I_END',m2=15e6),demand('LC1','J_END',m2=15e6),
            demand('LC2','I_END',m2=35e6),demand('LC2','J_END',m2=35e6))), angle_count=32)
        self.assertEqual(result.status,S1Status.NUMERIC_CANDIDATE_FOUND_NOT_FULL_TBDY)
        self.assertTrue(result.governing_state_id.startswith('LC2:'))

    def test_incomplete_case_population_rejected(self):
        with self.assertRaisesRegex(ValueError,'POPULATION_INCOMPLETE'):
            snapshot(demand_rows=(demand('LC1','I_END'),))

    def test_mixed_generation_rejected(self):
        with self.assertRaisesRegex(ValueError,'MIXED_MODEL_EPOCH_GENERATION'):
            snapshot(demand_rows=(demand('LC1','I_END',gen='GEN-2'),demand('LC1','J_END')))

    def test_case_identity_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError,'CASE_IDENTITY_MISMATCH'):
            row=demand('LC1','I_END')
            snapshot(demand_rows=(replace(row,evidence=replace(row.evidence,case_state_id='OTHER')),demand('LC1','J_END')))

    def test_modal_kind_rejected(self):
        row=demand('LC1','I_END')
        with self.assertRaisesRegex(ValueError,'SIMULTANEOUS_SIGNED_LINEAR_STATIC'):
            snapshot(demand_rows=(replace(row,evidence=replace(row.evidence,kind=DemandKind.RESPONSE_SPECTRUM_COMBINED)),demand('LC1','J_END')))

    def test_wrong_column_identity_rejected(self):
        row=demand('LC1','I_END')
        with self.assertRaisesRegex(ValueError,'MIXED_COLUMN_IDENTITY'):
            snapshot(demand_rows=(replace(row,column_id='C2'),demand('LC1','J_END')))

    def test_extreme_axial_demand_has_no_candidate(self):
        result=evaluate_s1_column(snapshot(demand_rows=(demand(n=15e6),demand(end='J_END',n=15e6))),angle_count=32)
        self.assertEqual(result.status,S1Status.NO_FEASIBLE_CANDIDATE)
        self.assertIsNone(result.selected_area_mm2)

    def test_layout_geometry_corner_count_and_minimum_spacing(self):
        inputs=ColumnRebarGeometryInputs(800,800,40,8)
        candidate=build_rectangular_column_rebar_geometry_candidate(inputs,diameter_mm=20,n_bars_dir2=7,n_bars_dir3=7)
        self.assertEqual(candidate.bar_count,24)
        self.assertAlmostEqual(candidate.as_total_mm2,24*math.pi*20*20/4)
        self.assertEqual(len({(b.x2_mm,b.x3_mm) for b in candidate.bars}),24)

    def test_ts500_c35_strength_block_factor(self):
        self.assertEqual(ts500_k1_for_fck_mpa(35),0.79)
        with self.assertRaises(ValueError): ts500_k1_for_fck_mpa(55)


class IndependentSectionOracle(unittest.TestCase):
    def test_production_strain_compatibility_matches_independent_strip_integration(self):
        layout=build_rectangular_column_rebar_geometry_candidate(
            ColumnRebarGeometryInputs(800,800,40,8),diameter_mm=20,n_bars_dir2=3,n_bars_dir3=3)
        mat=ColumnSectionMaterial(35,35/1.5,500/1.15)
        oracle_mat=OracleMaterial(35,35/1.5,500/1.15,0.79)
        obars=tuple(OracleBar(b.index,b.x2_mm,b.x3_mm,b.diameter_mm,b.area_mm2) for b in layout.bars)
        for angle,c in ((0,180),(33,320),(90,300)):
            expected=evaluate_state(width_mm=800,depth_mm=800,bars=obars,material=oracle_mat,
                                    theta_deg=angle,c_mm=c)
            actual=evaluate_rectangular_column_capacity_state(
                width_mm=800,depth_mm=800,bars=layout.bars,material=mat,
                neutral_axis_angle_deg=angle,neutral_axis_depth_c_mm=c)
            self.assertAlmostEqual(actual.n_compression_n,expected.n_n,delta=1.0)
            self.assertAlmostEqual(actual.m2_nmm,expected.m2_nmm,delta=1500.0)
            self.assertAlmostEqual(actual.m3_nmm,expected.m3_nmm,delta=1500.0)


if __name__ == '__main__': unittest.main()
