"""S1-C: exact-station PMM, existing native reader bridge, fail-closed proofs."""
from dataclasses import replace
from pathlib import Path
import unittest

from tbdy_column_core.contracts import DemandKind, EvidenceKey
from tbdy_column_core.physics.section_capacity import ColumnSectionMaterial
from tbdy_column_core.recorded_etabs import (
    RecordError, RowSemantics, read_historical_column_capture,
)
from tbdy_column_core.s1 import (
    DemandReadiness, DemandStationKey, QualifiedColumnDemand, S1ColumnSnapshot,
    S1Status, SourceClass, evaluate_s1_column,
)
from tbdy_column_core.s1_report import s1_report_json
from tbdy_column_core.station_compiler import stage_recorded_static_column

ANCHOR = EvidenceKey("a" * 64, "SYN-1", "SYN-GEN-1", "SYN-CASE-SET",
                     DemandKind.SIGNED_LINEAR_STATIC)
MAT = ColumnSectionMaterial(35, 35 / 1.5, 500 / 1.15)


def demand(case="L1", station=0, m2=25e6, m3=20e6, element="E1"):
    return QualifiedColumnDemand(
        state_id=f"{case}|{element}|{station}", column_id="C1",
        output_case=case,
        end_tag=("I_END" if station == 0 else "J_END"
                 if station == 3000 else "INTERIOR"),
        nd_compression_n=500_000, m2_nmm=m2, m3_nmm=m3,
        evidence=replace(ANCHOR, case_state_id=case),
        station_mm=station, element_id=element, element_station_mm=station,
        step_type="Single Value", step_number=0.0,
    )


def snapshot(*, cases=("L1",), rows=None, expected=None,
             source=SourceClass.SYNTHETIC_VALIDATION):
    if rows is None:
        rows = tuple(demand(c, s) for c in cases for s in (0, 1500, 3000))
    if expected is None:
        expected = tuple(DemandStationKey(c, "E1", s, s)
                         for c in cases for s in (0, 1500, 3000))
    return S1ColumnSnapshot(
        column_id="C1", evidence=ANCHOR, source_class=source,
        demand_readiness=DemandReadiness.FINAL_DESIGN_REVIEWED,
        basis_refs=("SYNTHETIC_REFERENCE_ONLY",), width_mm=400, depth_mm=400,
        clear_cover_mm=40, tie_diameter_mm=8, aggregate_max_mm=20,
        allowed_bar_diameters_mm=(20,), material=MAT,
        demands=rows, expected_case_ids=cases, expected_station_keys=expected,
    )


class AllStationNumericalTests(unittest.TestCase):
    def test_middle_station_governs_pmm_and_report(self):
        rows = (demand(station=0, m2=10e6),
                demand(station=1500, m2=60e6, m3=30e6),
                demand(station=3000, m2=15e6))
        result = evaluate_s1_column(snapshot(rows=rows), angle_count=32)
        self.assertEqual(result.status, S1Status.NUMERIC_CANDIDATE_FOUND_NOT_FULL_TBDY)
        self.assertEqual(result.evaluated_demand_count, 3)
        self.assertEqual(result.expected_station_count, 3)
        self.assertEqual(result.governing_station_mm, 1500)
        self.assertEqual(result.governing_element_id, "E1")
        self.assertIn('"governing_station_mm":1500', s1_report_json(result))
        self.assertFalse(result.full_tbd_y_qualified)

    def test_six_states_two_cases_all_evaluated(self):
        cases = ("L1", "L2")
        rows = tuple(demand(c, s, m2=55e6 if c == "L2" and s == 1500 else 12e6)
                     for c in cases for s in (0, 1500, 3000))
        result = evaluate_s1_column(snapshot(cases=cases, rows=rows), angle_count=32)
        self.assertEqual(result.evaluated_demand_count, 6)
        self.assertIn("L2", result.governing_state_id)

    def test_middle_missing_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "POPULATION_INCOMPLETE"):
            snapshot(rows=(demand(station=0), demand(station=3000)))

    def test_extra_station_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "POPULATION_INCOMPLETE"):
            snapshot(rows=tuple(demand(station=s) for s in (0, 1000, 1500, 3000)))

    def test_duplicate_physical_station_is_rejected(self):
        rows = tuple(demand(station=s) for s in (0, 1500, 3000))
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            snapshot(rows=rows + (replace(rows[1], state_id="another"),))

    def test_other_element_is_not_same_station(self):
        rows = list(demand(station=s) for s in (0, 1500, 3000))
        rows[1] = replace(rows[1], element_id="E2")
        with self.assertRaisesRegex(ValueError, "POPULATION_INCOMPLETE"):
            snapshot(rows=tuple(rows))

    def test_other_generation_is_not_same_population(self):
        rows = list(demand(station=s) for s in (0, 1500, 3000))
        rows[1] = replace(rows[1],
                          evidence=replace(rows[1].evidence, analysis_generation="OTHER"))
        with self.assertRaisesRegex(ValueError, "MIXED_MODEL"):
            snapshot(rows=tuple(rows))

    def test_modal_step_is_rejected_before_maths(self):
        with self.assertRaisesRegex(ValueError, "ENVELOPE_OR_NONSTATIC"):
            replace(demand(), step_type="Max")

    def test_half_physical_station_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_PHYSICAL"):
            replace(demand(station=1500), element_id=None)

    def test_station_requires_expected_census(self):
        old = snapshot()
        with self.assertRaisesRegex(ValueError, "EXPLICIT_STATION_CENSUS_REQUIRED"):
            replace(old, expected_station_keys=None)

    def test_recorded_review_string_cannot_unlock_pmm(self):
        result = evaluate_s1_column(snapshot(source=SourceClass.RECORDED_ETABS))
        self.assertEqual(result.status, S1Status.DEMAND_BASIS_BLOCKED)
        self.assertIn("REQUIRES_QUALIFIED_FINAL_DEMAND", result.reason)


class RealHistorical235StagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = (Path(__file__).parent / "fixtures" /
                       "column235_grav_ult_historical_subset.json")
        cls.population = read_historical_column_capture(cls.fixture)
        cls.expected = tuple(DemandStationKey("Grav_Ult", "235", s, s)
                             for s in (0.0, 2225.0, 4450.0))

    def stage(self, *, expected=None, case_ids=("Grav_Ult",), population=None):
        return stage_recorded_static_column(
            population or self.population, column_id="235",
            static_case_ids=case_ids,
            expected_station_keys=expected if expected is not None else self.expected,
            claimed_evidence=EvidenceKey("f"*64, "UNVERIFIED_EPOCH",
                                         "UNVERIFIED_GENERATION", "PROJECT_UNIVERSE",
                                         DemandKind.SIGNED_LINEAR_STATIC),
            width_mm=800, depth_mm=800, clear_cover_mm=40, tie_diameter_mm=8,
            aggregate_max_mm=20, allowed_bar_diameters_mm=(20,), material=MAT,
        )

    def test_three_historical_stations_preserved_exactly(self):
        staged = self.stage()
        self.assertEqual(staged.expected_station_count, 3)
        self.assertEqual(staged.excluded_extrema_count, 0)  # fixture is ONLY 3 Grav_Ult rows
        self.assertEqual([x.station_mm for x in staged.snapshot.demands],
                         [0.0, 2225.0, 4450.0])
        self.assertEqual({x.end_tag for x in staged.snapshot.demands}, {"STATION"})
        self.assertAlmostEqual(staged.snapshot.demands[0].nd_compression_n,
                               4398029.75509404, places=4)
        self.assertFalse(staged.final_design_demand_proven)

    def test_historical_capture_remains_blocked_and_no_selection(self):
        r = evaluate_s1_column(self.stage().snapshot, angle_count=32)
        self.assertEqual(r.status, S1Status.DEMAND_BASIS_BLOCKED)
        self.assertIsNone(r.selected_candidate_id)
        self.assertIsNone(r.governing_utilization)

    def test_forged_final_design_label_cannot_unlock_capture(self):
        staged = self.stage()
        forged = replace(staged.snapshot, demand_readiness=DemandReadiness.FINAL_DESIGN_REVIEWED,
                         basis_refs=("SELF_DECLARED",))
        self.assertEqual(evaluate_s1_column(forged).status, S1Status.DEMAND_BASIS_BLOCKED)

    def test_middle_station_missing_from_expected_rejected(self):
        with self.assertRaisesRegex(RecordError, "MISSING_EXTRA"):
            self.stage(expected=(self.expected[0], self.expected[2]))

    def test_modal_max_row_cannot_join_signed_static_population(self):
        bad = replace(self.population.rows[0],
                      semantics=RowSemantics.MODAL_OR_EXTREMUM_NOT_SIMULTANEOUS,
                      step_type="Max")
        altered = replace(self.population, rows=(bad,)+self.population.rows[1:])
        with self.assertRaisesRegex(RecordError, "NON_SIMULTANEOUS"):
            self.stage(population=altered)

    def test_case_scope_does_not_silently_shrink(self):
        with self.assertRaisesRegex(RecordError, "SCOPE_MISMATCH"):
            self.stage(case_ids=("OTHER",))

    def test_wrong_component_cannot_be_staged(self):
        with self.assertRaisesRegex(RecordError, "COLUMN_ID_NOT"):
            stage_recorded_static_column(
                self.population, column_id="236", static_case_ids=("Grav_Ult",),
                expected_station_keys=self.expected, claimed_evidence=ANCHOR,
                width_mm=800, depth_mm=800, clear_cover_mm=40, tie_diameter_mm=8,
                aggregate_max_mm=20, allowed_bar_diameters_mm=(20,), material=MAT,
            )


if __name__ == "__main__":
    unittest.main()
