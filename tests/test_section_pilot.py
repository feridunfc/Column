"""Sprint B1: independent RC section states, root and radial verification."""
from __future__ import annotations
from dataclasses import replace
import json
from math import pi
import unittest
from examples.section_pilot import fixture_problem
from tbdy_column_core.application.services import calculate_section
from tbdy_column_core.domain.quantities import Length,Force,Moment,Angle,Stress,ElasticModulus
from tbdy_column_core.domain.section_models import BarPoint,DesignSteelLaw
from tbdy_column_core.domain.identity import RevisionRef
from tbdy_column_core.domain.section_requests import (
    SectionStatus,AtStrainState,EnvelopeAtAxialForce,RadialCapacityAtAxialForce,
)
from tbdy_column_core.reporting.section_report import (
    section_report_json,section_report_html,
)
from tests.independent.oracle import (
    OracleBar,OracleMaterial,evaluate_state,solve_fixed_p_state,
    radial_capacity_dense_convex,
)


def oracle_fixture(problem):
    section=problem.section
    bars=tuple(OracleBar(i,b.x2.as_mm,b.x3.as_mm,b.diameter.as_mm,
                         pi*b.diameter.as_mm**2/4)
               for i,b in enumerate(section.longitudinal.bars))
    return bars,OracleMaterial(35,35/1.5,420/1.15,.79)


class SectionB1Tests(unittest.TestCase):
    def test_geometry_asymmetric_and_two_cage_populations(self):
        for layout,expected in (("A",4),("B",6)):
            p=fixture_problem(layout=layout)
            shape=p.section.profile
            self.assertEqual(shape.area.as_mm2,240000)
            self.assertAlmostEqual(shape.i22.as_cm4,720000)
            self.assertAlmostEqual(shape.i33.as_cm4,320000)
            self.assertEqual(len(p.section.longitudinal.bars),expected)
            self.assertAlmostEqual(p.section.longitudinal.total_area.as_mm2,
                                   expected*pi*100)

    def test_independent_three_strain_states_two_layouts(self):
        for layout in ("A","B"):
            for theta,c in ((0,200),(33,240),(90,200)):
                p=fixture_problem(layout=layout,
                      request=AtStrainState(Angle.deg(theta),Length.mm(c)))
                actual=calculate_section(p)
                bars,material=oracle_fixture(p)
                expected=evaluate_state(
                    width_mm=400,depth_mm=600,bars=bars,material=material,
                    theta_deg=theta,c_mm=c,
                )
                self.assertEqual(actual.status,SectionStatus.NUMERIC_STATE)
                self.assertEqual(len(actual.states),1)
                state=actual.states[0]
                self.assertAlmostEqual(state.n.as_n,expected.n_n,delta=1.)
                self.assertAlmostEqual(state.m2.as_nmm,expected.m2_nmm,delta=2000.)
                self.assertAlmostEqual(state.m3.as_nmm,expected.m3_nmm,delta=2000.)
                self.assertIsNone(state.axial_residual)
                self.assertFalse(actual.full_column_design_pass)

    def test_cm_mm_geometry_sources_numerically_equal(self):
        a=fixture_problem(layout="B",units="mm")
        b=fixture_problem(layout="B",units="cm")
        x,y=calculate_section(a),calculate_section(b)
        self.assertEqual(x.status,y.status)
        self.assertAlmostEqual(x.states[0].n.as_n,y.states[0].n.as_n,delta=1e-8)
        self.assertAlmostEqual(x.states[0].m2.as_nmm,y.states[0].m2.as_nmm,delta=.001)
        self.assertAlmostEqual(x.states[0].m3.as_nmm,y.states[0].m3.as_nmm,delta=.001)

    def test_bar_order_does_not_change_result(self):
        p=fixture_problem(layout="B")
        rearranged=replace(p.section.longitudinal,
                           bars=tuple(reversed(p.section.longitudinal.bars)))
        alternative=replace(p,section=replace(p.section,longitudinal=rearranged))
        self.assertEqual(calculate_section(p),calculate_section(alternative))

    def test_cover_overlap_duplicates_rejected(self):
        p=fixture_problem()
        layout=p.section.longitudinal
        with self.assertRaises(ValueError):
            replace(layout,bars=layout.bars+(layout.bars[0],))
        outside=replace(layout.bars[0],x2=Length.mm(-190))
        with self.assertRaises(ValueError):
            replace(p.section,longitudinal=replace(layout,bars=(outside,)+layout.bars[1:]))
        with self.assertRaises(ValueError):
            replace(layout,bars=layout.bars+(replace(layout.bars[0],
                bar_id="EXTRA",x2=Length.mm(layout.bars[0].x2.as_mm+1)),))

    def test_missing_and_mixed_steel_law_are_unsupported(self):
        p=fixture_problem(layout="B")
        first=replace(p.section.longitudinal.bars[0],steel_ref="UNKNOWN")
        malformed=replace(p.section.longitudinal,
                          bars=(first,)+p.section.longitudinal.bars[1:])
        a=calculate_section(replace(p,section=replace(p.section,longitudinal=malformed)))
        self.assertEqual(a.status,SectionStatus.UNSUPPORTED_MATERIAL)
        self.assertTrue(any("UNKNOWN_BAR_STEEL" in s for s in a.issues))
        another=DesignSteelLaw("B500",Stress.mpa(500/1.15),
                               ElasticModulus.mpa(200000),
                               RevisionRef("steel-law","B500","rev1"))
        laws=replace(p.section.material,
                     steel_laws=p.section.material.steel_laws+(another,))
        second=replace(p.section.longitudinal.bars[0],steel_ref="B500")
        mix=replace(p.section.longitudinal,
                    bars=(second,)+p.section.longitudinal.bars[1:])
        b=calculate_section(replace(p,section=replace(
            p.section,material=laws,longitudinal=mix)))
        self.assertEqual(b.status,SectionStatus.UNSUPPORTED_MATERIAL)
        self.assertIn("MIXED_BAR_STEEL_CONSTITUTIVE_LAWS",b.issues)

    def test_fixed_n_roots_independent_oracle(self):
        p=fixture_problem(layout="B",angle_count=8,
             request=EnvelopeAtAxialForce(Force.kn(500)))
        actual=calculate_section(p)
        self.assertEqual(actual.status,SectionStatus.COMPLETE_ENVELOPE,
                         actual.issues[:5])
        self.assertEqual(len(actual.states),8)
        bars,material=oracle_fixture(p)
        for i in (0,2):
            theta=i*45.
            independent=solve_fixed_p_state(
                width_mm=400,depth_mm=600,bars=bars,material=material,
                theta_deg=theta,target_n=500000,axial_tolerance_n=1,
                scan_count=360,
            )
            self.assertIsNotNone(independent)
            state=actual.states[i]
            self.assertAlmostEqual(state.n.as_n,independent.n_n,delta=1.5)
            self.assertAlmostEqual(state.m2.as_nmm,independent.m2_nmm,delta=2500)
            self.assertAlmostEqual(state.m3.as_nmm,independent.m3_nmm,delta=2500)
            self.assertLessEqual(abs(state.axial_residual.as_n),1)

    def test_radial_angle_convergence_and_dense_oracle(self):
        radii=[]
        for count in (72,144,288):
            p=fixture_problem(layout="B",angle_count=count,
                request=RadialCapacityAtAxialForce(
                    Force.kn(500),Moment.kn_m(40),Moment.kn_m(20)))
            result=calculate_section(p)
            self.assertEqual(result.status,SectionStatus.COMPLETE_RADIAL,
                             result.issues[:4])
            radii.append(result.radial_capacity.as_nmm)
            self.assertEqual(len(result.states),count)
            self.assertFalse(result.full_column_design_pass)
        self.assertLess(abs(radii[1]-radii[2]),.03*radii[2])
        p=fixture_problem(layout="B")
        bars,material=oracle_fixture(p)
        oracle=radial_capacity_dense_convex(
            width_mm=400,depth_mm=600,bars=bars,material=material,
            target_n=500000,demand_m2_nmm=40000000,demand_m3_nmm=20000000,
            angle_count=144,root_scan_count=160,axial_tolerance_n=1,
        )
        self.assertEqual(oracle.status,"PROVEN")
        self.assertAlmostEqual(radii[2],oracle.capacity_nmm,
                               delta=.03*oracle.capacity_nmm)

    def test_zero_moment_no_infinite_capacity(self):
        p=fixture_problem(angle_count=8,request=RadialCapacityAtAxialForce(
            Force.kn(500),Moment.nmm(0),Moment.nmm(0)))
        r=calculate_section(p)
        self.assertEqual(r.status,SectionStatus.UNDEFINED_MOMENT_DIRECTION)
        self.assertIsNone(r.radial_capacity)
        payload=json.loads(section_report_json(r))
        self.assertIsNone(payload["radial_capacity_nmm"])
        self.assertIn("UNDEFINED_MOMENT_DIRECTION",payload["issues"])

    def test_extreme_axial_demand_not_misrepresented_as_physically_outside(self):
        p=fixture_problem(angle_count=8,
            request=EnvelopeAtAxialForce(Force.kn(10000)))
        r=calculate_section(p)
        self.assertIn(r.status,(SectionStatus.NUMERIC_UNRESOLVED,SectionStatus.PARTIAL_ENVELOPE))
        self.assertNotEqual(r.status.value,"OUTSIDE_AXIAL_CAPACITY")
        self.assertFalse(r.full_column_design_pass)
        self.assertTrue(r.issues)

    def test_max_iterations_is_not_silently_ignored(self):
        p=fixture_problem(angle_count=8,max_iterations=1,
            request=EnvelopeAtAxialForce(Force.kn(500)))
        r=calculate_section(p)
        self.assertEqual(r.applied_policy.max_iterations,1)
        self.assertNotEqual(r.status,SectionStatus.COMPLETE_ENVELOPE)

    def test_same_result_json_html_and_second_section(self):
        for b,h in ((400,600),(450,650)):
            p=fixture_problem(layout="B",b_mm=b,h_mm=h)
            r=calculate_section(p)
            parsed=json.loads(section_report_json(r))
            html=section_report_html(r)
            self.assertIn(f'R{b}x{h}B',r.section_ref.identifier)
            self.assertEqual(parsed["geometry"][0]["value"],b)
            self.assertEqual(parsed["geometry"][1]["value"],h)
            self.assertIn(str(r.states[0].n.as_n),html)
            self.assertIn("NOT EVALUATED: slenderness",html)
            self.assertIn("schema",html)
            self.assertFalse(parsed["full_column_design_pass"])
            self.assertEqual(section_report_json(r),section_report_json(r))
            self.assertEqual(section_report_html(r),section_report_html(r))


if __name__=="__main__": unittest.main()
