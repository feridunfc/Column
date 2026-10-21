"""Show all 3 recorded Grav_Ult stations without falsely selecting rebar."""
from dataclasses import asdict
from pathlib import Path
import json

from tbdy_column_core.contracts import DemandKind, EvidenceKey
from tbdy_column_core.physics.section_capacity import ColumnSectionMaterial
from tbdy_column_core.recorded_etabs import read_historical_column_capture
from tbdy_column_core.s1 import DemandStationKey, evaluate_s1_column
from tbdy_column_core.station_compiler import stage_recorded_static_column
from tbdy_column_core.s1_report import s1_report_json


def main():
    p = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "column235_grav_ult_historical_subset.json"
    pop = read_historical_column_capture(p)
    scope = tuple(DemandStationKey("Grav_Ult", "235", s, s) for s in (0.0, 2225.0, 4450.0))
    staged = stage_recorded_static_column(
        pop, column_id="235", static_case_ids=("Grav_Ult",),
        expected_station_keys=scope,
        claimed_evidence=EvidenceKey("f"*64, "UNVERIFIED_EPOCH", "UNVERIFIED_GENERATION",
                                     "PROJECT_UNIVERSE", DemandKind.SIGNED_LINEAR_STATIC),
        width_mm=800, depth_mm=800, clear_cover_mm=40, tie_diameter_mm=8,
        aggregate_max_mm=20, allowed_bar_diameters_mm=(20,),
        material=ColumnSectionMaterial(35, 35/1.5, 500/1.15),
    )
    print(json.dumps({
        "column": "235", "historical_station_mm": [d.station_mm for d in staged.snapshot.demands],
        "state_count": len(staged.snapshot.demands),
        "complete_model_state_proven": False, "final_design_demand_proven": False,
        "s1_result": json.loads(s1_report_json(evaluate_s1_column(staged.snapshot))),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
