"""S1-F: consume ORIGINAL gateway replay public contract and A18/A19/A20 outputs.

The fake provider here has the exact read_context/fixture API of the old
etabs_gateway FixtureReplayProvider. It is a *contract fake*, not evidence of
the original package being executed inside Codespaces.
"""
from dataclasses import replace
from hashlib import sha256
from json import dumps, loads
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

from tbdy_column_core.physics.end_moment_ratio import build_exact_static_end_moment_ratio
from tbdy_column_core.s1f_gateway import (
    A18_AUTHORITY, A19_AUTHORITY, A20_AUTHORITY,
    S1FStatus, reconcile_existing_gateway_replay,
)
from tbdy_column_core.physics.rebar_selection import ColumnDemandState
from tests.test_s1e import fixture


GATEWAY_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "existing_gateway_context_v1.json"


def gateway_provider():
    # This file is copied without modification from the OLD gateway's
    # tests/fixtures/gateway_context_v1.json; validate its signed envelope
    # using the exact SHA-256 canonicalization documented by old replay.py.
    envelope = loads(GATEWAY_FIXTURE_PATH.read_text(encoding="utf-8"))
    signed = {k: envelope[k] for k in ("schema_version", "fixture_type", "context")}
    checksum = sha256(dumps(signed, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    if checksum != envelope["sha256"]:
        raise ValueError("GATEWAY_FIXTURE_SHA256_MISMATCH")
    model_json = envelope["context"]["model"]
    model = NS(
        has_open_model=model_json["has_open_model"],
        model_path=model_json["model_path"],
        units=NS(**model_json["units"]) if model_json["units"] else None,
    )
    ctx = NS(model=model)
    fixt = NS(schema_version="1.0", fixture_type="ETABS_GATEWAY_CONTEXT",
              sha256=envelope["sha256"], context=ctx)
    return NS(fixture=fixt, fingerprint=fixt.sha256, read_context=lambda: ctx)


def canonical_end(s, case, tag):
    d = next(d for d in s.demands if d.output_case == case and d.end_tag == tag)
    return ColumnDemandState(
        state_id=d.state_id, component_id=d.column_id, output_case=case,
        case_type="DesignStaticLinearExact", step_type=None, step_number=None,
        station_m=d.station_mm / 1000.0, end_tag=tag,
        nd_compression_n=d.nd_compression_n, m2_nmm=d.m2_nmm,
        m3_nmm=d.m3_nmm, source_identity=f"SYN:{case}:{tag}",
    )


def products(*, cases=("L1",)):
    s, _ = fixture(cases=cases)
    a18 = []
    a19 = []
    a20 = []
    for axis in ("M2", "M3"):
        for end in ("BOTTOM", "TOP"):
            a18.append(NS(
                component_id="C1", end_tag=end, local_bending_axis=axis,
                authority=A18_AUTHORITY, disposition="READY", alpha=1.0,
                numerator_column_i_over_l_m3=0.01,
                denominator_beam_i_over_l_m3=0.01,
                source_refs=("SYNTHETIC_A18_TOPOLOGY_FIXTURE",),
            ))
        a19.append(NS(
            component_id="C1", local_bending_axis=axis,
            authority=A19_AUTHORITY, disposition="READY",
            alpha_bottom=1.0, alpha_top=1.0,
            one_end_hinged=False, k=0.8, free_length_ln_mm=3000.0,
            effective_length_lk_mm=2400.0,
            sway_classification="SWAY_PREVENTED",
            source_refs=("SYNTHETIC_A19_FIXTURE",),
        ))
    for case in cases:
        i, j = canonical_end(s, case, "I_END"), canonical_end(s, case, "J_END")
        for axis in ("M2", "M3"):
            ev = build_exact_static_end_moment_ratio(
                i_end=i, j_end=j, axis=axis,
                analysis_result_ref=f"SYNTHETIC_ANALYSIS_RESULT:{case}",
                source_refs=(f"SYNTHETIC_A20:{case}:{axis}",),
            )
            a20.append(NS(
                component_id="C1", local_bending_axis=axis,
                output_case=case, authority=A20_AUTHORITY, disposition="READY",
                analysis_result_ref=f"SYNTHETIC_ANALYSIS_RESULT:{case}",
                evidence=ev, source_refs=(f"SYNTHETIC_A20:{case}:{axis}",),
            ))
    return s, a18, a19, a20


def run_replay(*, provider=None, s=None, a18=None, a19=None, a20=None):
    if s is None:
        s, a18, a19, a20 = products()
    return reconcile_existing_gateway_replay(
        provider if provider is not None else gateway_provider(),
        s, a18_rows=a18, a19_rows=a19, a20_rows=a20,
    )


class OriginalGatewayReplayCompatibility(unittest.TestCase):
    def test_genuine_old_fixture_sha_matches_payload(self):
        p = gateway_provider()
        self.assertEqual(p.fixture.sha256,
                         "dfecde1c184a34e2395bb50747b38c8d0e3ab96b20327c7f00ca7a6209ec7172")

    def test_replays_a18_a19_a20_without_ever_certifying_edb(self):
        result = run_replay()
        self.assertEqual(result.status, S1FStatus.REPLAY_RECONCILED_NO_LIVE_PROOF)
        self.assertEqual({x.axis for x in result.axes}, {"M2","M3"})
        self.assertEqual({x.axis for x in result.end_moments}, {"M2","M3"})
        self.assertEqual({round(x.k,3) for x in result.axes}, {0.8})
        self.assertEqual({round(x.lk_mm) for x in result.axes}, {2400})
        self.assertEqual({round(x.ratio,2) for x in result.end_moments},
                         {-0.5, 0.25})
        self.assertFalse(result.edb_bytes_verified)
        self.assertFalse(result.analysis_generation_verified)
        self.assertFalse(result.real_design_basis_verified)
        self.assertIn("fixture.edb",result.model_path_metadata)

    def test_two_output_cases_are_independently_reconciled(self):
        s, a18, a19, a20 = products(cases=("L1","L2"))
        result = run_replay(s=s, a18=a18, a19=a19, a20=a20)
        self.assertEqual(result.status, S1FStatus.REPLAY_RECONCILED_NO_LIVE_PROOF)
        self.assertEqual(len(result.end_moments),4)

    def test_a18_numerator_denominator_wrong_blocks(self):
        s, a18, a19, a20 = products()
        a18[0] = NS(**{**vars(a18[0]), "alpha": 2.0})
        r=run_replay(s=s,a18=a18,a19=a19,a20=a20)
        self.assertEqual(r.status, S1FStatus.BLOCKED)
        self.assertIn("A18_ALPHA",r.reason)

    def test_a19_effective_length_wrong_blocks(self):
        s, a18, a19, a20 = products()
        a19[0] = NS(**{**vars(a19[0]), "effective_length_lk_mm": 3000})
        r=run_replay(s=s,a18=a18,a19=a19,a20=a20)
        self.assertEqual(r.status, S1FStatus.BLOCKED)
        self.assertIn("A19_K_OR_LK",r.reason)

    def test_a19_k_wrong_blocks(self):
        s, a18, a19, a20 = products()
        a19[0] = NS(**{**vars(a19[0]), "k": 1.0})
        r=run_replay(s=s,a18=a18,a19=a19,a20=a20)
        self.assertEqual(r.status, S1FStatus.BLOCKED)

    def test_missing_topology_axis_blocks(self):
        s, a18, a19, a20 = products()
        self.assertEqual(run_replay(s=s,a18=a18[:3],a19=a19,a20=a20).status,
                         S1FStatus.BLOCKED)

    def test_missing_a20_case_axis_blocks(self):
        s, a18, a19, a20 = products()
        self.assertEqual(run_replay(s=s,a18=a18,a19=a19,a20=a20[:1]).status,
                         S1FStatus.BLOCKED)

    def test_wrong_a20_sign_ratio_blocks(self):
        s, a18, a19, a20 = products()
        e=a20[0].evidence
        a20[0]=NS(**{**vars(a20[0]),"evidence":replace(e,moment_ratio_m1_over_m2=0.5)})
        r=run_replay(s=s,a18=a18,a19=a19,a20=a20)
        self.assertEqual(r.status,S1FStatus.BLOCKED)
        self.assertIn("A20_SIGNED",r.reason)

    def test_a20_wrong_end_id_blocks(self):
        s, a18, a19, a20 = products()
        e=a20[0].evidence
        a20[0]=NS(**{**vars(a20[0]),"evidence":replace(e,i_end_state_id="OTHER")})
        self.assertEqual(run_replay(s=s,a18=a18,a19=a19,a20=a20).status,
                         S1FStatus.BLOCKED)

    def test_wrong_materialization_authority_blocks(self):
        s, a18, a19, a20 = products()
        a19[0] = NS(**{**vars(a19[0]), "authority": "FAKE"})
        self.assertEqual(run_replay(s=s,a18=a18,a19=a19,a20=a20).status,
                         S1FStatus.BLOCKED)

    def test_missing_gateway_model_blocks(self):
        s, a18, a19, a20 = products()
        provider = gateway_provider()
        provider.fixture.context.model.has_open_model=False
        self.assertEqual(run_replay(provider=provider,s=s,a18=a18,a19=a19,a20=a20).status,
                         S1FStatus.BLOCKED)

    def test_gateway_provider_fingerprint_mismatch_blocks(self):
        s, a18, a19, a20 = products()
        provider=gateway_provider()
        provider.fingerprint="0"*64
        self.assertEqual(run_replay(provider=provider,s=s,a18=a18,a19=a19,a20=a20).status,
                         S1FStatus.BLOCKED)

    def test_old_context_alone_cannot_claim_current_model(self):
        r=run_replay()
        self.assertEqual(r.reason,"ORIGINAL_GATEWAY_REPLAY_A18_A19_A20_NUMERICALLY_RECONCILED_ONLY")
        self.assertFalse(r.real_design_basis_verified)


if __name__=="__main__":
    unittest.main()
