"""S1-K synthetic pipeline: typed full-chain tests, never real design authority."""
from dataclasses import replace
import unittest

from tbdy_column_core.contracts import EvidenceKey
from tbdy_column_core.s1 import SourceClass, DemandReadiness
from tbdy_column_core.s1_pipeline import (
    S1PipelineStatus, run_s1_numeric_preview,
)
from tbdy_column_core.s1e_basis import (
    S1EBasisStatus, prepare_s1e_basis,
)
from tests.test_s1e import fixture


class S1KFullChainSyntheticTests(unittest.TestCase):
    def test_full_chain_covers_every_raw_station_and_returns_numeric_trial(self):
        snap, axes = fixture()
        r = run_s1_numeric_preview(snap, axis_facts=axes)
        self.assertEqual(r.status, S1PipelineStatus.NUMERIC_CANDIDATE_PREVIEW_NOT_DESIGN_PASS)
        self.assertEqual(r.raw_station_count, 3)
        self.assertEqual(r.case_count, 1)
        self.assertEqual(r.numeric_demand_count, len(r.derived_states))
        self.assertEqual(
            {(d.output_case, d.station_m) for d in r.derived_states},
            {("L1", 0), ("L1", 1.5), ("L1", 3)},
        )
        self.assertFalse(r.final_design_demand_proven)
        self.assertFalse(r.full_ts500_tbdy_design_pass)
        self.assertGreater(r.evaluated_candidate_count, 0)
        self.assertTrue(r.open_engineering_checks)
        self.assertTrue(r.governing_state_id)

    def test_two_cases_are_preserved_not_mixed(self):
        snap, axes = fixture(cases=("L1", "L2"))
        r = run_s1_numeric_preview(snap, axis_facts=axes)
        self.assertEqual(r.status, S1PipelineStatus.NUMERIC_CANDIDATE_PREVIEW_NOT_DESIGN_PASS)
        self.assertEqual(r.case_count, 2)
        self.assertEqual(r.raw_station_count, 6)
        self.assertEqual({d.output_case for d in r.derived_states}, {"L1","L2"})
        self.assertFalse(r.full_ts500_tbdy_design_pass)

    def test_sign_branches_do_not_go_back_into_raw_station_snapshot(self):
        snap, axes = fixture()
        changed = tuple(replace(d, m2_nmm=0.0, m3_nmm=0.0)
                        if d.end_tag == "I_END" else d
                        for d in snap.demands)
        raw = replace(snap, demands=changed)
        r = run_s1_numeric_preview(raw, axis_facts=axes)
        self.assertEqual(r.status, S1PipelineStatus.NUMERIC_CANDIDATE_PREVIEW_NOT_DESIGN_PASS)
        self.assertEqual(r.raw_station_count, 3)
        self.assertGreater(r.numeric_demand_count, 3)
        self.assertGreater(r.branch_count, 0)
        self.assertEqual(len({d.state_id for d in r.derived_states}),
                         len(r.derived_states))
        self.assertEqual(
            {d.station_m for d in r.derived_states}, {0, 1.5, 3},
        )
        self.assertFalse(r.full_ts500_tbdy_design_pass)

    def test_end_force_difference_above_5_percent_does_not_invent_constant_nd(self):
        snap, axes = fixture()
        source = replace(
            snap, demands=tuple(
                replace(d, nd_compression_n=625_000.0)
                if d.end_tag == "J_END" else d
                for d in snap.demands
            ),
        )
        basis = prepare_s1e_basis(source, axis_facts=axes)
        self.assertEqual(basis.status, S1EBasisStatus.READY_SYNTHETIC_BASIS_NOT_REAL_RELEASE)
        r = run_s1_numeric_preview(source, axis_facts=axes)
        self.assertEqual(r.status, S1PipelineStatus.NUMERIC_CANDIDATE_PREVIEW_NOT_DESIGN_PASS)
        self.assertIn(625_000.0, {d.nd_compression_n for d in r.derived_states})
        self.assertIn(500_000.0, {d.nd_compression_n for d in r.derived_states})
        self.assertFalse(r.final_design_demand_proven)

    def test_long_column_axis_specific_magnification_remains_synthetic(self):
        snap, axes = fixture(length=6000.0)
        r = run_s1_numeric_preview(snap, axis_facts=axes)
        self.assertEqual(r.status, S1PipelineStatus.NUMERIC_CANDIDATE_PREVIEW_NOT_DESIGN_PASS)
        self.assertEqual(r.case_count, 1)
        self.assertFalse(r.final_design_demand_proven)

    def test_recorded_etabs_source_cannot_be_promoted_using_synthetic_axes(self):
        snap, axes = fixture(source=SourceClass.RECORDED_ETABS)
        r = run_s1_numeric_preview(snap, axis_facts=axes)
        self.assertEqual(r.status, S1PipelineStatus.SOURCE_BLOCKED)
        self.assertEqual(r.numeric_demand_count, 0)
        self.assertIsNone(r.selected_candidate_id)

    def test_no_pass_for_raw_demands_labeled_final_by_hand(self):
        snap, axes = fixture()
        r = run_s1_numeric_preview(
            replace(snap, demand_readiness=DemandReadiness.FINAL_DESIGN_REVIEWED,
                    basis_refs=("FAKE-REVIEW",)), axis_facts=axes,
        )
        self.assertEqual(r.status, S1PipelineStatus.SOURCE_BLOCKED)
        self.assertFalse(r.full_ts500_tbdy_design_pass)

    def test_missing_axis_or_mixed_model_evidence_blocks_before_pmm(self):
        snap, axes = fixture()
        r = run_s1_numeric_preview(snap, axis_facts=axes[:1])
        self.assertEqual(r.status, S1PipelineStatus.BASIS_BLOCKED)
        tampered = replace(axes[0], evidence=replace(
            axes[0].evidence, model_sha256="f"*64,
        ))
        r = run_s1_numeric_preview(snap, axis_facts=(tampered, axes[1]))
        self.assertEqual(r.status, S1PipelineStatus.BASIS_BLOCKED)
        self.assertIsNone(r.selected_candidate_id)

    def test_no_implicit_station_to_physical_i_j_translation(self):
        snap, axes = fixture()
        src = replace(snap, demands=tuple(
            replace(d, end_tag="STATION") for d in snap.demands
        ))
        r = run_s1_numeric_preview(src, axis_facts=axes)
        self.assertEqual(r.status, S1PipelineStatus.BASIS_BLOCKED)
        self.assertFalse(r.final_design_demand_proven)

    def test_invalid_numeric_sampling_is_not_silently_coerced(self):
        snap, axes = fixture()
        with self.assertRaisesRegex(ValueError, "Angle count"):
            run_s1_numeric_preview(snap, axis_facts=axes, angle_count=10)

    def test_pipeline_deterministic_for_identical_synthetic_inputs(self):
        snap, axes = fixture()
        a=run_s1_numeric_preview(snap, axis_facts=axes)
        b=run_s1_numeric_preview(snap, axis_facts=axes)
        self.assertEqual(a, b)

if __name__ == "__main__":
    unittest.main()
