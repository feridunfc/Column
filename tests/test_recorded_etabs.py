"""S1-B regression tests: prior native-provider contract and real historical subset."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import unittest

from tbdy_column_core.recorded_etabs import (
    RecordError, RowSemantics, import_historical_column_capture,
    import_old_b5_force_population, read_historical_column_capture,
    recorded_force_report_json,
)

FIXTURE = Path(__file__).parent / "fixtures" / "column235_grav_ult_historical_subset.json"


def fake_legacy_b5(*, rows=None, case="STATIC_CASE", names=("C1",)):
    if rows is None:
        rows = [{
            "Story": "S1", "Column": "C1", "UniqueName": "C1", "OutputCase": case,
            "CaseType": "LinStatic", "StepType": None, "StepNumber": None,
            "Station": 0.0, "ElemStation": 0.0, "Element": "C1",
            "P": -100.0, "V2": 2.0, "V3": 3.0,
            "T": 1.0, "M2": 11.0, "M3": -12.0,
        }]
    return SimpleNamespace(
        contract="TBDY_B5_COLUMN_FORCE_RESULT_POPULATION_V1",
        case_name=case,
        expected_unique_names=names, observed_unique_names=names,
        evidence_ref="b5-column-force-population:sha256:" + "f"*64,
        rows=tuple(rows),
    )


class HistoricalETABS235AdapterTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_three_real_grav_ult_stations_are_read_only_and_not_qualified(self):
        captured = read_historical_column_capture(FIXTURE)
        self.assertEqual(captured.column_ids, ("235",))
        self.assertEqual(len(captured.rows), 3)
        self.assertEqual({r.station_mm for r in captured.rows}, {0.0, 2225.0, 4450.0})
        self.assertEqual(len(captured.single_value_rows), 3)
        self.assertEqual(len(captured.extrema_rows), 0)
        self.assertFalse(captured.native_population_proven)
        self.assertFalse(captured.final_design_demand_proven)
        self.assertIn("engineering_release_qualified", captured.summary())

    def test_original_native_pressure_sign_and_units_not_swapped(self):
        first = read_historical_column_capture(FIXTURE).rows[0]
        self.assertAlmostEqual(first.n_compression_n, 4398029.75509404, places=4)
        self.assertAlmostEqual(first.m2_nmm, 17417663.77805542, places=3)
        self.assertAlmostEqual(first.m3_nmm, -28627450.8387755, places=3)
        self.assertEqual(first.semantics, RowSemantics.SINGLE_VALUE_NEEDS_CASE_AUTHORITY)

    def test_midstation_is_not_dropped_into_s1_ij_only(self):
        captured = read_historical_column_capture(FIXTURE)
        self.assertEqual(len([r for r in captured.rows if r.station_mm == 2225]), 1)
        self.assertIn("S1_I_J_ONLY_CANNOT_SILENTLY_DROP_INTERIOR_STATION",
                      captured.summary()["blockers"])

    def test_historical_digest_is_not_claimed_as_current_generation(self):
        captured = read_historical_column_capture(FIXTURE)
        out = recorded_force_report_json(captured)
        self.assertIn('"final_design_demand_proven":false', out)
        self.assertIn('"engineering_release_qualified":false', out)
        self.assertIn("CURRENT_ANALYSIS_GENERATION_AND_MODEL_BINDING_NOT_PROVEN", out)

    def test_missing_row_rejected(self):
        data = deepcopy(self.data)
        data["raw_frame_forces"].pop()
        with self.assertRaisesRegex(RecordError, "ROW_COUNT"):
            import_historical_column_capture(data)

    def test_missing_middle_station_even_with_amended_row_count_rejected(self):
        data = deepcopy(self.data)
        data["raw_frame_forces"].pop(1)
        data["expected_row_count"] = 2
        with self.assertRaisesRegex(RecordError, "STATION_POPULATION_MISMATCH"):
            import_historical_column_capture(data)

    def test_duplicate_station_rejected(self):
        data = deepcopy(self.data)
        data["raw_frame_forces"].append(deepcopy(data["raw_frame_forces"][0]))
        data["expected_row_count"] = 4
        with self.assertRaisesRegex(RecordError, "DUPLICATE_EXACT_FORCE_ROW"):
            import_historical_column_capture(data)

    def test_native_compression_sign_mismatch_rejected(self):
        data = deepcopy(self.data)
        data["raw_frame_forces"][0]["n_compression_positive_kn"] = "99999"
        with self.assertRaisesRegex(RecordError, "NATIVE_P_SIGN_CONFLICT"):
            import_historical_column_capture(data)

    def test_wrong_component_is_rejected(self):
        data = deepcopy(self.data)
        data["raw_frame_forces"][0]["column"] = "OTHER"
        with self.assertRaisesRegex(RecordError, "COLUMN_IDENTITY_MISMATCH"):
            import_historical_column_capture(data)

    def test_nonfinite_native_force_rejected(self):
        data = deepcopy(self.data)
        data["raw_frame_forces"][0]["m2_knm"] = "NaN"
        with self.assertRaisesRegex(RecordError, "nonfinite"):
            import_historical_column_capture(data)

    def test_missing_case_expectation_rejected(self):
        data = deepcopy(self.data)
        data["expected_case_steps"] = []
        with self.assertRaisesRegex(RecordError, "MISSING_CASE_STEP_CENSUS"):
            import_historical_column_capture(data)


class UnchangedB5FactualOwnerBridgeTests(unittest.TestCase):
    def test_original_typed_b5_provider_rows_are_accepted(self):
        p = import_old_b5_force_population(fake_legacy_b5(), source_unit="kN_cm_kNm")
        self.assertTrue(p.native_population_proven)
        self.assertFalse(p.final_design_demand_proven)
        self.assertEqual(p.rows[0].n_compression_n, 100000.0)
        self.assertEqual(p.rows[0].m2_nmm, 11000000.0)
        self.assertEqual(p.rows[0].m3_nmm, -12000000.0)

    def test_native_unit_not_verified_rejected(self):
        with self.assertRaisesRegex(RecordError, "UNITS"):
            import_old_b5_force_population(fake_legacy_b5(), source_unit="UNKNOWN")

    def test_native_wrong_case_rejected(self):
        row = dict(fake_legacy_b5().rows[0]); row["OutputCase"] = "OTHER"
        with self.assertRaisesRegex(RecordError, "OUTPUT_CASE"):
            import_old_b5_force_population(fake_legacy_b5(rows=[row]), source_unit="kN_cm_kNm")

    def test_spectrum_max_never_promoted_to_simultaneous(self):
        row = dict(fake_legacy_b5().rows[0])
        row["CaseType"], row["StepType"] = "LinRespSpec", "Max"
        p = import_old_b5_force_population(fake_legacy_b5(rows=[row]), source_unit="kN_cm_kNm")
        self.assertIs(p.rows[0].semantics, RowSemantics.MODAL_OR_EXTREMUM_NOT_SIMULTANEOUS)

    def test_native_missing_expected_column_rejected(self):
        with self.assertRaisesRegex(RecordError, "COLUMN_POPULATION_MISMATCH"):
            import_old_b5_force_population(
                fake_legacy_b5(names=("C1", "C2")), source_unit="kN_cm_kNm"
            )

    def test_native_duplicate_result_identity_rejected(self):
        row = fake_legacy_b5().rows[0]
        with self.assertRaisesRegex(RecordError, "DUPLICATE_EXACT_FORCE_ROW"):
            import_old_b5_force_population(
                fake_legacy_b5(rows=[row, row]), source_unit="kN_cm_kNm"
            )

    def test_unsupported_native_case_semantics_rejected(self):
        row = dict(fake_legacy_b5().rows[0]); row["CaseType"] = "Nonlinear"
        with self.assertRaisesRegex(RecordError, "UNSUPPORTED_CASE_OR_STEP"):
            import_old_b5_force_population(
                fake_legacy_b5(rows=[row]), source_unit="kN_cm_kNm"
            )


if __name__ == "__main__":
    unittest.main()
