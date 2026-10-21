import unittest
from dataclasses import replace

from tbdy_column_core.contracts import (
    ColumnAxialContribution, DemandKind, EvidenceKey, GateStatus, StoryStabilityFacts,
)
from tbdy_column_core.engine import execute_first_pass
from tbdy_column_core.stability import check_nonsway_ts500_7_13
from tbdy_column_core.report import report_json, report_sha256


E = EvidenceKey("a" * 64, "E1", "A1", "G+Q+E_static_X", DemandKind.SIGNED_LINEAR_STATIC)


def facts(*, e=E, delta=10.0, shear=300_000.0, lengths=(3000.0, 4000.0)):
    return StoryStabilityFacts(
        story_id="S1", direction="X", delta_i_mm=delta, v_fi_n=shear,
        expected_column_ids=("C1", "C2"),
        columns=(ColumnAxialContribution("C1", 1_000_000, lengths[0], e),
                 ColumnAxialContribution("C2", 2_000_000, lengths[1], e)),
        evidence=e, uncracked_sections=True, first_order_analysis=True,
    )


class StoryStabilityTests(unittest.TestCase):
    def test_two_different_column_lengths_normative_sum(self):
        actual = check_nonsway_ts500_7_13(facts())
        self.assertAlmostEqual(actual.phi, 1/24, places=12)
        self.assertEqual(actual.status, GateStatus.NONSWAY_ESTABLISHED)

    def test_using_story_height_for_every_column_changes_answer(self):
        self.assertNotAlmostEqual(check_nonsway_ts500_7_13(facts()).phi,
                                  check_nonsway_ts500_7_13(facts(lengths=(3000, 3000))).phi)

    def test_above_005_not_artificial_025_reanalysis_threshold(self):
        result = check_nonsway_ts500_7_13(facts(delta=18))
        self.assertEqual(result.status, GateStatus.NONSWAY_NOT_ESTABLISHED)
        self.assertGreater(result.phi, 0.05)

    def test_exact_005_boundary(self):
        result = check_nonsway_ts500_7_13(facts(delta=12))
        self.assertAlmostEqual(result.phi, 0.05)
        self.assertEqual(result.status, GateStatus.NONSWAY_ESTABLISHED)

    def test_spectrum_result_is_not_silently_treated_as_signed_static(self):
        s = facts(e=replace(E, kind=DemandKind.RESPONSE_SPECTRUM_COMBINED))
        r = check_nonsway_ts500_7_13(s)
        self.assertEqual(r.status, GateStatus.EVIDENCE_BLOCKED)
        self.assertIsNone(r.phi)

    def test_mixed_generation_blocked(self):
        s = facts()
        s = replace(s, columns=(s.columns[0], replace(s.columns[1], evidence=replace(E, analysis_generation="A2"))))
        self.assertEqual(check_nonsway_ts500_7_13(s).status, GateStatus.EVIDENCE_BLOCKED)

    def test_incomplete_population_blocked(self):
        s = facts()
        s = replace(s, columns=s.columns[:1])
        self.assertEqual(check_nonsway_ts500_7_13(s).reason, "STORY_POPULATION_INCOMPLETE")

    def test_duplicate_population_blocked(self):
        s = facts()
        s = replace(s, columns=(s.columns[0], s.columns[0]))
        self.assertEqual(check_nonsway_ts500_7_13(s).reason, "DUPLICATE_COLUMN_ID")

    def test_cracked_analysis_blocked(self):
        s = replace(facts(), uncracked_sections=False)
        self.assertEqual(check_nonsway_ts500_7_13(s).reason, "UNQUALIFIED_ANALYSIS_BASIS")

    def test_tension_requires_review(self):
        s = facts()
        s = replace(s, columns=(replace(s.columns[0], ndi_n=-1_000), s.columns[1]))
        self.assertEqual(check_nonsway_ts500_7_13(s).status, GateStatus.EVIDENCE_BLOCKED)

    def test_invalid_story_shear_rejected(self):
        with self.assertRaises(ValueError):
            facts(shear=0)

    def test_report_is_deterministic_and_never_full_column_approved(self):
        p = execute_first_pass((facts(),))
        self.assertFalse(p.full_column_design_completed)
        self.assertEqual(report_sha256(p), report_sha256(p))
        self.assertIn('"engineering_release_qualified":false', report_json(p))

    def test_mixed_case_across_stories_rejected(self):
        a = facts()
        b = replace(facts(e=replace(E, case_state_id="OTHER_CASE")), story_id="S2")
        with self.assertRaises(ValueError):
            execute_first_pass((a, b))

    def test_unknown_or_envelope_evidence_blocked(self):
        for kind in (DemandKind.ENVELOPE, DemandKind.UNKNOWN):
            s = facts(e=replace(E, kind=kind))
            self.assertEqual(check_nonsway_ts500_7_13(s).status, GateStatus.EVIDENCE_BLOCKED)

    def test_wrong_source_digest_in_one_member_blocked(self):
        s = facts()
        mutated = replace(s.columns[1], evidence=replace(E, model_sha256="b" * 64))
        self.assertEqual(check_nonsway_ts500_7_13(replace(s, columns=(s.columns[0], mutated))).status,
                         GateStatus.EVIDENCE_BLOCKED)


if __name__ == "__main__":
    unittest.main()
