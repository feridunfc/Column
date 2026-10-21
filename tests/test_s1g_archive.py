"""Offline evidence ledger tests. Full 60-row archive is user-provided, not CI-generated."""
from hashlib import sha256
from json import loads
from pathlib import Path
import os
import unittest

from tools.legacy_audit.s1g_archive import (
    ArchiveEvidenceError, KNOWN_RECORDED_SHA, KNOWN_CUTSET_SHA,
    KNOWN_STABILITY_SHA, audit_original_235, audit_archive_zip,
)

ROOT=Path(__file__).parent
LEDGER=ROOT/"fixtures"/"column235_s1g_archived_evidence.json"


class S1GArchiveLedgerTests(unittest.TestCase):
    def test_pinned_original_source_identifiers(self):
        receipt=loads(LEDGER.read_text(encoding="utf-8"))
        self.assertEqual(receipt["recorded_source_sha256"],KNOWN_RECORDED_SHA)
        self.assertEqual(receipt["cutset_source_sha256"],KNOWN_CUTSET_SHA)
        self.assertEqual(receipt["stability_source_sha256"],KNOWN_STABILITY_SHA)

    def test_archive_counts_do_not_prove_design_universe(self):
        r=loads(LEDGER.read_text(encoding="utf-8"))
        self.assertEqual((r["observed_raw_frameforce_rows"],
                          r["observed_signed_single_value_rows"],
                          r["observed_max_min_rows"]),(60,12,48))
        self.assertEqual(r["stations_mm"],[0,2225,4450])
        self.assertFalse(r["engineering_design_release_qualified"])

    def test_original_model_candidate_is_not_falsely_rebound(self):
        r=loads(LEDGER.read_text(encoding="utf-8"))
        self.assertNotEqual(r["recorded_model_sha256"],
                            r["cutset_candidate_model_sha256"])
        self.assertFalse(r["recorded_model_to_candidate_authority_rebound"])
        self.assertFalse(r["current_result_epoch_proven"])

    def test_historical_raw_and_separate_design_moments_stay_distinct(self):
        r=loads(LEDGER.read_text(encoding="utf-8"))
        self.assertNotEqual(r["grav_ult_first_raw_m3_knm"],
                            r["separate_design_m3_knm"])
        self.assertAlmostEqual(r["grav_ult_first_raw_m3_knm"],-28.6274508388,places=6)

    def test_story_comparison_is_not_global_sway_proof(self):
        r=loads(LEDGER.read_text(encoding="utf-8"))
        self.assertAlmostEqual(r["story_operand_difference_kn"],82463.2776)
        self.assertFalse(r["global_sway_proven"])
        self.assertEqual(r["modal_m6b"],"OPEN")

    def test_mutated_untrusted_archives_are_rejected_at_byte_boundary(self):
        for bad in (b"{}", b"not json", b" "):
            with self.assertRaisesRegex(ArchiveEvidenceError,"SHA256_MISMATCH"):
                audit_original_235(bad,bad,bad)

    def test_prior_three_row_fixture_does_not_claim_full_capture(self):
        old=loads((ROOT/"fixtures"/"column235_grav_ult_historical_subset.json").read_text())
        r=loads(LEDGER.read_text(encoding="utf-8"))
        self.assertEqual(old["expected_row_count"],3)
        self.assertEqual(r["observed_raw_frameforce_rows"],60)
        self.assertEqual(old["original_file_sha256"],r["recorded_source_sha256"])

    @unittest.skipUnless(os.environ.get("COLUMN_S1G_SOURCE_ZIP"),
                         "Full old archival ZIP not checked into the public source tree")
    def test_full_original_60_row_archive_when_provided(self):
        audited=audit_archive_zip(os.environ["COLUMN_S1G_SOURCE_ZIP"])
        self.assertEqual(audited.archived_frameforce_row_count,60)
        self.assertEqual(audited.single_value_row_count,12)
        self.assertEqual(audited.extrema_row_count,48)
        self.assertFalse(audited.full_design_authorized)


if __name__=="__main__":
    unittest.main()
