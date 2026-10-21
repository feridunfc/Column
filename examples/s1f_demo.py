"""Demonstration of OLD gateway contract (synthetic materialization, no COM)."""
from json import dumps
from tests.test_s1f import gateway_provider, products
from tools.legacy_audit.s1f_gateway import reconcile_existing_gateway_replay

def main() -> None:
    snapshot, a18, a19, a20 = products()
    result = reconcile_existing_gateway_replay(
        gateway_provider(), snapshot,
        a18_rows=a18, a19_rows=a19, a20_rows=a20,
    )
    print(dumps({
        "status": result.status.value,
        "column": result.column_id,
        "replay_only": True,
        "gateway_context_sha256": result.gateway_context_fingerprint,
        "axes": [
            {"axis": x.axis, "alpha_bottom": x.alpha_bottom,
             "alpha_top": x.alpha_top, "k": x.k, "lk_mm": x.lk_mm}
            for x in result.axes
        ],
        "end_moment_ratios": [
            {"case": x.case, "axis": x.axis, "m1_m2": x.ratio}
            for x in result.end_moments
        ],
        "edb_bytes_verified": result.edb_bytes_verified,
        "analysis_generation_verified": result.analysis_generation_verified,
        "real_design_basis_verified": result.real_design_basis_verified,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
