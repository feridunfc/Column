"""Synthetic S1 demonstration only. THIS IS NOT COLUMN 235."""
from tbdy_column_core.contracts import DemandKind, EvidenceKey
from tbdy_column_core.physics.section_capacity import ColumnSectionMaterial
from tbdy_column_core.s1 import (
    DemandReadiness, QualifiedColumnDemand, S1ColumnSnapshot, SourceClass, evaluate_s1_column,
)
from tbdy_column_core.s1_report import s1_report_json


def main() -> None:
    anchor = EvidenceKey("f" * 64, "SYN-EPOCH", "SYN-GEN", "PROJECT_CASE_SET",
                         DemandKind.SIGNED_LINEAR_STATIC)
    one = EvidenceKey("f" * 64, "SYN-EPOCH", "SYN-GEN", "SYN-COMBO",
                      DemandKind.SIGNED_LINEAR_STATIC)
    result = evaluate_s1_column(S1ColumnSnapshot(
        column_id="SYN-C1", evidence=anchor, source_class=SourceClass.SYNTHETIC_VALIDATION,
        demand_readiness=DemandReadiness.FINAL_DESIGN_REVIEWED,
        basis_refs=("SYNTHETIC_FIXTURE_ONLY",),
        width_mm=400.0, depth_mm=400.0, clear_cover_mm=40.0,
        tie_diameter_mm=8.0, aggregate_max_mm=20.0,
        allowed_bar_diameters_mm=(20.0,),
        material=ColumnSectionMaterial(35.0, 35.0/1.5, 500.0/1.15),
        expected_case_ids=("SYN-COMBO",),
        demands=(
            QualifiedColumnDemand("SYN-I", "SYN-C1", "SYN-COMBO", "I_END",
                                  500_000, 25_000_000, 20_000_000, one),
            QualifiedColumnDemand("SYN-J", "SYN-C1", "SYN-COMBO", "J_END",
                                  500_000, 25_000_000, 20_000_000, one),
        ),
    ), angle_count=32)
    print(s1_report_json(result))


if __name__ == "__main__":
    main()
