"""Read-only demo: three historical Column 235 Grav_Ult stations, NOT design authority."""
from pathlib import Path
from tbdy_column_core.recorded_etabs import read_historical_column_capture, recorded_force_report_json

def main() -> None:
    path = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "column235_grav_ult_historical_subset.json"
    print(recorded_force_report_json(read_historical_column_capture(path)))

if __name__ == "__main__":
    main()
