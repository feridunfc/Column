"""S1-E: source-scope joins and automatic A18/A19/A20 arithmetic, no fake native pass."""
from dataclasses import replace
from math import isclose
import unittest

from tbdy_column_core.contracts import EvidenceKey, DemandKind
from tbdy_column_core.physics.effective_length import EndRestraintMemberContribution
from tbdy_column_core.physics.section_capacity import ColumnSectionMaterial
from tbdy_column_core.s1 import (
    S1ColumnSnapshot, SourceClass, DemandReadiness,
    DemandStationKey, QualifiedColumnDemand,
)
from tbdy_column_core.s1d_mechanics import (
    preview_ts500_static_mechanics, S1DStatus,
)
from tbdy_column_core.s1e_basis import (
    S1EAxisFacts, S1EBasisStatus, prepare_s1e_basis,
)

E = EvidenceKey("d"*64, "E-SYN", "GEN-SYN", "SYN-CASE-SET",
                DemandKind.SIGNED_LINEAR_STATIC)
MAT = ColumnSectionMaterial(35,35/1.5,500/1.15)


def fixture(*, length=3000.0, cases=("L1",), source=SourceClass.SYNTHETIC_VALIDATION):
    rows=[]
    for case in cases:
        for station, end, m2, m3 in (
            (0.0, "I_END", 10e6, 5e6),
            (1500.0, "INTERIOR", 15e6, 12e6),
            (3000.0, "J_END", -20e6, 20e6),
        ):
            rows.append(QualifiedColumnDemand(
                state_id=f"{case}:E1:{station}", column_id="C1",
                output_case=case, end_tag=end,
                nd_compression_n=500_000,m2_nmm=m2,m3_nmm=m3,
                evidence=replace(E, case_state_id=case),
                element_id="E1",station_mm=station,
                element_station_mm=station,step_type="Single Value",
            ))
    s=S1ColumnSnapshot(
        column_id="C1", evidence=E, source_class=source,
        demand_readiness=DemandReadiness.RAW_FIRST_ORDER,
        basis_refs=(),width_mm=400,depth_mm=400,clear_cover_mm=40,
        tie_diameter_mm=8,aggregate_max_mm=20,
        allowed_bar_diameters_mm=(20,),material=MAT,
        demands=tuple(rows),expected_case_ids=cases,
        expected_station_keys=tuple(DemandStationKey(c,"E1",p,p)
                                     for c in cases for p in (0,1500,3000)),
    )
    def contribution(role,axis,end):
        # Both I/L*modifier = 0.01m^3, so alpha=1 at each end.
        return EndRestraintMemberContribution(
            member_id=f"{role}:{axis}:{end}",
            member_role=role,
            inertia_m4=(.03 if role=="COLUMN" else .04),
            member_length_m=(3 if role=="COLUMN" else 2),
            inertia_factor=(1 if role=="COLUMN" else .5),
            source_refs=(f"SYN-TOPOLOGY:{role}:{axis}:{end}",),
        )
    a=[]
    for axis in ("M2","M3"):
        a.append(S1EAxisFacts(
            axis=axis,evidence=E,
            bottom_columns=(contribution("COLUMN",axis,"BOTTOM"),),
            bottom_beams=(contribution("BEAM",axis,"BOTTOM"),),
            top_columns=(contribution("COLUMN",axis,"TOP"),),
            top_beams=(contribution("BEAM",axis,"TOP"),),
            free_length_ln_mm=length,
            free_length_producer_ref="SYN-A19-FREE-LENGTH",
            sway_classification="SWAY_PREVENTED",
            sway_producer_ref="SYN-A17-SWAY-X-Y",
            physical_end_topology_ref="SYN-A18-TOPOLOGY-JOINTS",
            one_end_hinged=False,horizontal_load_between_ends=False,
            ec_mpa=34_000,ic_mm4=400**4/12,creep_ratio_rm=.25,
            mechanics_source_ref="SYN-A22-MECHANICS",
        ))
    return s,tuple(a)


class ProducerDerivation(unittest.TestCase):
    def test_independent_alpha_k_lk_numeric(self):
        s,a=fixture()
        r=prepare_s1e_basis(s,axis_facts=a)
        self.assertEqual(r.status,S1EBasisStatus.READY_SYNTHETIC_BASIS_NOT_REAL_RELEASE)
        self.assertFalse(r.real_etabs_basis_qualified)
        self.assertEqual(len(r.axes),2)
        for b in r.axes:
            self.assertAlmostEqual(b.alpha_bottom,1.0,places=12)
            self.assertAlmostEqual(b.alpha_top,1.0,places=12)
            self.assertAlmostEqual(b.k,.8,places=12)
            self.assertAlmostEqual(b.lk_mm,2400.0,places=12)

    def test_same_case_end_ratios_produced_from_signed_m2_m3(self):
        s,a=fixture()
        r=prepare_s1e_basis(s,axis_facts=a)
        c=r.cases[0]
        ratios={q.axis:q.moment_ratio_m1_over_m2 for q in c.end_moment_ratios}
        self.assertAlmostEqual(ratios["M2"],-.5,places=12)
        self.assertAlmostEqual(ratios["M3"],.25,places=12)
        self.assertEqual(c.slenderness_status,"PROVEN_SLENDERNESS_EFFECTS_NEGLIGIBLE")
        self.assertEqual(c.magnification_pairs,())

    def test_preview_receives_automatically_derived_slenderness(self):
        s,a=fixture()
        result=prepare_s1e_basis(s,axis_facts=a)
        preview=preview_ts500_static_mechanics(
            s,slenderness=result.cases[0].slenderness_basis)
        self.assertEqual(preview.status,S1DStatus.NUMERIC_MECHANICS_PREVIEW_NOT_FINAL)
        self.assertFalse(preview.final_design_demand_proven)
        self.assertEqual(preview.intermediate_station_count,1)

    def test_longer_free_length_requires_axis_specific_magnification(self):
        s,a=fixture(length=6000.0)
        r=prepare_s1e_basis(s,axis_facts=a)
        self.assertEqual(r.status,S1EBasisStatus.READY_SYNTHETIC_BASIS_NOT_REAL_RELEASE)
        c=r.cases[0]
        # Lk=4.8m; lambda=40; M2 double curvature ratio -0.5,
        # neglect limit 40; M3 single curvature ratio +0.25,
        # neglect limit 31, so only M3 needs moment magnification.
        self.assertEqual(len(c.magnification_pairs),3)
        self.assertTrue(all(p.m2 is None and p.m3 is not None
                            for p in c.magnification_pairs))
        numeric=preview_ts500_static_mechanics(
            s,slenderness=c.slenderness_basis,
            magnification=c.magnification_pairs)
        self.assertEqual(numeric.status,S1DStatus.NUMERIC_MECHANICS_PREVIEW_NOT_FINAL)
        self.assertEqual(numeric.axis_magnification_count,3)
        self.assertFalse(numeric.final_design_demand_proven)

    def test_two_cases_stay_separate(self):
        s,a=fixture(cases=("L1","L2"))
        r=prepare_s1e_basis(s,axis_facts=a)
        self.assertEqual(len(r.cases),2)
        self.assertEqual([v.output_case for v in r.cases],["L1","L2"])
        self.assertTrue(all(len(z.end_moment_ratios)==2 for z in r.cases))


class FailsClosed(unittest.TestCase):
    def test_historical_etabs_does_not_use_synthetic_bases_to_pass(self):
        s,a=fixture(source=SourceClass.RECORDED_ETABS)
        r=prepare_s1e_basis(s,axis_facts=a)
        self.assertEqual(r.status,S1EBasisStatus.SOURCE_BLOCKED)
        self.assertFalse(r.automatic_numeric_basis_available)

    def test_mismatched_analysis_generation_blocks(self):
        s,a=fixture()
        r=prepare_s1e_basis(s,axis_facts=(replace(
            a[0],evidence=replace(a[0].evidence,analysis_generation="GEN-2")),a[1]))
        self.assertEqual(r.status,S1EBasisStatus.SOURCE_BLOCKED)

    def test_incomplete_local_axes_blocks(self):
        s,a=fixture()
        r=prepare_s1e_basis(s,axis_facts=a[:1])
        self.assertEqual(r.status,S1EBasisStatus.SOURCE_BLOCKED)

    def test_free_length_missing_from_a19_blocks(self):
        s,a=fixture()
        r=prepare_s1e_basis(s,axis_facts=(replace(a[0],free_length_ln_mm=None),a[1]))
        self.assertEqual(r.status,S1EBasisStatus.MISSING_PHYSICAL_TOPOLOGY)

    def test_end_topology_missing_blocks(self):
        s,a=fixture()
        r=prepare_s1e_basis(s,axis_facts=(replace(a[0],physical_end_topology_ref=None),a[1]))
        self.assertEqual(r.status,S1EBasisStatus.MISSING_PHYSICAL_TOPOLOGY)

    def test_sway_permitted_requires_full_story_aggregates(self):
        s,a=fixture()
        r=prepare_s1e_basis(s,axis_facts=(replace(a[0],sway_classification="SWAY_PERMITTED"),a[1]))
        self.assertEqual(r.status,S1EBasisStatus.UNSUPPORTED_SWAY_NEEDS_STORY_AGGREGATES)

    def test_no_guess_horizontal_load_presence(self):
        s,a=fixture(length=6000)
        r=prepare_s1e_basis(s,axis_facts=(replace(a[0],horizontal_load_between_ends=None),a[1]))
        self.assertEqual(r.status,S1EBasisStatus.MISSING_REQUIRED_MECHANICS)

    def test_missing_connected_beam_cannot_assume_rigid_restraint(self):
        s,a=fixture()
        r=prepare_s1e_basis(s,axis_facts=(replace(a[0],bottom_beams=()),a[1]))
        self.assertEqual(r.status,S1EBasisStatus.MISSING_REQUIRED_MECHANICS)
        self.assertIn("beam",r.reason.lower())

    def test_unqualified_physical_i_end_prevents_ratio(self):
        s,a=fixture()
        rows=list(s.demands)
        rows[0]=replace(rows[0],end_tag="STATION")
        r=prepare_s1e_basis(replace(s,demands=tuple(rows)),axis_facts=a)
        self.assertEqual(r.status,S1EBasisStatus.MISSING_REQUIRED_MECHANICS)
        self.assertIn("I_END",r.reason)

    def test_final_reviewed_facts_cannot_reenter_second_order(self):
        s,a=fixture()
        r=prepare_s1e_basis(replace(
            s,demand_readiness=DemandReadiness.FINAL_DESIGN_REVIEWED),axis_facts=a)
        self.assertEqual(r.status,S1EBasisStatus.SOURCE_BLOCKED)


if __name__=="__main__":
    unittest.main()
