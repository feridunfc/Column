"""v1.2 B — provided 400x600 RC section, independent strip oracle."""
from dataclasses import replace
from math import pi
import unittest
from tbdy_column_core.domain.quantities import Length,Force,Moment,Stress,ElasticModulus
from tbdy_column_core.domain.section_models import RectangularSection,ConcreteMaterial,RebarSteel,DesignMaterial,BarPoint,LongitudinalLayout,RCSection
from tbdy_column_core.domain.tolerances import NumericalPolicy
from tbdy_column_core.engineering.section_adapter import SectionKernelAdapter
from tbdy_column_core.engineering.section_solver import SectionCapacityProblem,calculate_section,section_capacity_report_json
from tests.independent.oracle import OracleBar,OracleMaterial,evaluate_state,radial_capacity_dense_convex

def fixture(units="mm",variant=1):
    f=Length.mm if units=="mm" else Length.cm
    k=1 if units=="mm" else .1
    section=RectangularSection(f(400*k),f(600*k))
    mat=DesignMaterial(ConcreteMaterial(Stress.mpa(35)),
        RebarSteel(Stress.mpa(500),ElasticModulus.mpa(200000)),
        Stress.mpa(35/1.5),Stress.mpa(500/1.15),.003,.79,"TS500-SECTION")
    xy=[(-150,-250),(150,-250),(-150,250),(150,250)]
    if variant==2: xy += [(0,-250),(0,250),(-150,0),(150,0)]
    bars=tuple(BarPoint(str(i),f(x*k),f(y*k),f(20*k),"LONGITUDINAL")
               for i,(x,y) in enumerate(xy))
    rc=RCSection("RC-400x600",section,mat,LongitudinalLayout(section,f(30*k),f(8*k),bars))
    policy=NumericalPolicy(Length.mm(.001),Force.n(1),Moment.nmm(2000),1e-6)
    return rc,policy

class Pilot(unittest.TestCase):
    def test_area_and_inertia_for_asymmetric_section(self):
        rc,p=fixture()
        self.assertEqual(rc.profile.area.as_mm2,240000)
        self.assertAlmostEqual(rc.profile.i22.as_mm4,400*600**3/12)
        self.assertAlmostEqual(rc.profile.i33.as_mm4,600*400**3/12)
    def test_two_layouts_independent_gauss_strip_oracle(self):
        for variant in (1,2):
            rc,p=fixture(variant=variant)
            obs=tuple(OracleBar(i,b.x2.as_mm,b.x3.as_mm,b.diameter.as_mm,pi*b.diameter.as_mm**2/4)
                for i,b in enumerate(rc.longitudinal.bars))
            om=OracleMaterial(35,35/1.5,500/1.15,.79)
            for angle,c in ((0,200),(33,320),(90,450)):
                expected=evaluate_state(width_mm=400,depth_mm=600,bars=obs,
                    material=om,theta_deg=angle,c_mm=c)
                result=calculate_section(SectionCapacityProblem(rc,angle,Length.mm(c),p))
                self.assertAlmostEqual(result.state_n.as_n,expected.n_n,delta=1)
                self.assertAlmostEqual(result.state_m2.as_nmm,expected.m2_nmm,delta=2000)
                self.assertAlmostEqual(result.state_m3.as_nmm,expected.m3_nmm,delta=2000)
                self.assertEqual(result.bar_count,len(obs))
                self.assertFalse(result.full_column_design_pass)
                self.assertEqual(section_capacity_report_json(result),section_capacity_report_json(result))
    def test_mm_cm_produce_same_capacity_and_report(self):
        x,p=fixture("mm",2)
        y,_=fixture("cm",2)
        self.assertEqual(x,y)
        result1=calculate_section(SectionCapacityProblem(x,33,Length.mm(320),p))
        result2=calculate_section(SectionCapacityProblem(y,33,Length.cm(32),p))
        self.assertEqual(result1,result2)
        self.assertEqual(section_capacity_report_json(result1),section_capacity_report_json(result2))
    def test_invalid_bars_overlap_and_cover(self):
        rc,p=fixture()
        with self.assertRaises(ValueError):
            replace(rc.longitudinal,bars=rc.longitudinal.bars+(rc.longitudinal.bars[0],))
        outside=replace(rc.longitudinal.bars[0],x2=Length.mm(-195))
        with self.assertRaises(ValueError):
            replace(rc.longitudinal,bars=(outside,)+rc.longitudinal.bars[1:])
    def test_reference_transfer_r_cross_f(self):
        m2,m3=SectionKernelAdapter.shift_moment_reference(
            Force.kn(100),Moment.kn_m(20),Moment.kn_m(10),
            offset_old_to_new_2=Length.cm(10),offset_old_to_new_3=Length.cm(20))
        self.assertEqual(m2,Moment.nmm(0))
        self.assertEqual(m3,Moment.kn_m(20))
    def test_handedness_and_policy_fail_closed(self):
        rc,p=fixture()
        with self.assertRaises(ValueError):SectionKernelAdapter(rc,-1,1)
        with self.assertRaises(ValueError):SectionCapacityProblem(rc,0,Length.mm(200),replace(p,max_iterations=50))

    def test_both_transverse_axes_reversed_are_normalized(self):
        rc,p=fixture(variant=2)
        normal=SectionKernelAdapter(rc).fixed_state(33,Length.mm(320))
        reverse=SectionKernelAdapter(rc,-1,-1).fixed_state(33,Length.mm(320))
        self.assertAlmostEqual(normal.n_compression_n,reverse.n_compression_n,delta=.001)
        self.assertAlmostEqual(normal.m2_nmm,reverse.m2_nmm,delta=.01)
        self.assertAlmostEqual(normal.m3_nmm,reverse.m3_nmm,delta=.01)

    def test_fixed_axial_envelope_is_separate_numeric_result(self):
        rc,p=fixture()
        result=calculate_section(SectionCapacityProblem(
            rc,33,Length.mm(320),replace(p,angle_count=8),
            target_axial=Force.kn(500),
            radial_demand_m2=Moment.kn_m(40),
            radial_demand_m3=Moment.kn_m(20),
        ))
        self.assertIsNotNone(result.angle_step_deg)
        self.assertIsNotNone(result.axial_residual)
        self.assertFalse(result.full_column_design_pass)

    def test_pmm_radial_capacity_independent_dense_oracle(self):
        # Independent 144-direction Gauss-Legendre + all-bracket solver
        # vs production 72-direction polygon/monotone hull/ray solver.
        for variant in (1,2):
            rc,p=fixture(variant=variant)
            obs=tuple(OracleBar(i,b.x2.as_mm,b.x3.as_mm,
                                b.diameter.as_mm,pi*b.diameter.as_mm**2/4)
                      for i,b in enumerate(rc.longitudinal.bars))
            oracle=radial_capacity_dense_convex(
                width_mm=400,depth_mm=600,bars=obs,
                material=OracleMaterial(35,35/1.5,500/1.15,.79),
                target_n=500_000,demand_m2_nmm=40_000_000,
                demand_m3_nmm=20_000_000,angle_count=144,
                root_scan_count=160,axial_tolerance_n=1.0,
            )
            result=calculate_section(SectionCapacityProblem(
                rc,33,Length.mm(320),p,
                target_axial=Force.kn(500),
                radial_demand_m2=Moment.kn_m(40),
                radial_demand_m3=Moment.kn_m(20),
            ))
            self.assertEqual(oracle.status,"PROVEN")
            self.assertTrue(result.converged)
            self.assertEqual(result.radial_status,"PROVEN")
            self.assertIsNotNone(result.radial_capacity)
            self.assertAlmostEqual(
                result.radial_capacity.as_nmm,oracle.capacity_nmm,
                delta=.03*oracle.capacity_nmm,
            )
            self.assertFalse(result.full_column_design_pass)

if __name__=="__main__":unittest.main()
