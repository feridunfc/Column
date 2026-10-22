"""B5: sampled radial origin/ray geometry guards and adverse numerical cases.

No live data and no changes to the pinned TS500 strain physics.
"""
from __future__ import annotations
import json
import unittest
from dataclasses import replace
from math import pi
from types import SimpleNamespace
from unittest.mock import patch

from examples.section_pilot import fixture_problem
from tbdy_column_core.application.services import calculate_section
from tbdy_column_core.domain.quantities import Force, Moment
from tbdy_column_core.domain.section_requests import (
    RadialCapacityAtAxialForce, SectionStatus,
    RadialHullStatus, RadialHullEvidence,
)
from tbdy_column_core.engineering.radial_geometry import (
    audit_radial_moment_hull, radial_boundary_alignment_residual
)
from tbdy_column_core.engineering.section_adapter import (
    RootScanAudit, SectionKernelAdapter
)
from tbdy_column_core.reporting.section_report import (
    section_report_json, section_report_html
)


def points(data):
    return tuple(SimpleNamespace(m2_nmm=float(x), m3_nmm=float(y)) for x,y in data)


class B5RadialSafetyTests(unittest.TestCase):

    def audit(self, data, tol=1000.):
        return audit_radial_moment_hull(
            points(data),
            moment_abs_tolerance=Moment.nmm(tol),
            relative_tolerance=0.,
        )

    def test_cardinal_points_strictly_enclose_origin(self):
        data=((0.,2e6),(2e6,0.),(0.,-2e6),(-2e6,0.))
        x=self.audit(data)
        self.assertEqual(x.status,RadialHullStatus.ORIGIN_STRICT_INTERIOR_SAMPLED)
        self.assertEqual(x.usable_direction_count,4)
        self.assertEqual(x.near_origin_point_count,0)
        self.assertAlmostEqual(x.maximum_direction_gap.as_rad,pi/2,places=12)
        self.assertAlmostEqual(x.interior_margin.as_rad,pi/2,places=12)

    def test_one_side_hull_never_generates_a_positive_radial_claim(self):
        x=self.audit(((8e6,2e6),(12e6,-3e6),(15e6,1e6),(10e6,-1e6)))
        self.assertEqual(x.status,RadialHullStatus.ORIGIN_NOT_INTERIOR_SAMPLED)
        self.assertLessEqual(x.interior_margin.as_rad,0.)
        self.assertIsNone(x.boundary_alignment_residual)

    def test_origin_on_boundary_and_collinear_hulls_fail_closed(self):
        boundary=self.audit(((0.,2e6),(2e6,0.),(0.,-2e6)))
        self.assertEqual(boundary.status,RadialHullStatus.ORIGIN_NOT_INTERIOR_SAMPLED)
        self.assertAlmostEqual(boundary.interior_margin.as_rad,0.,places=12)
        collinear=self.audit(((1e6,0.),(-2e6,0.),(3e6,0.)))
        self.assertNotEqual(collinear.status,RadialHullStatus.ORIGIN_STRICT_INTERIOR_SAMPLED)
        with self.assertRaises(ValueError):
            replace(boundary,boundary_alignment_residual=Moment.nmm(0))

    def test_policy_near_origin_filter_is_conservative(self):
        x=self.audit(((100.,0.),(0.,-100.),(-100.,0.),(0.,100.)),tol=1000.)
        self.assertEqual(x.status,RadialHullStatus.DEGENERATE_SAMPLED_HULL)
        self.assertEqual(x.near_origin_point_count,4)
        self.assertIsNone(x.maximum_direction_gap)
        with self.assertRaises(TypeError):
            audit_radial_moment_hull(points(((1.,2.),)),moment_abs_tolerance=1.,
                                     relative_tolerance=0.)
        with self.assertRaises(ValueError):
            self.audit(((float("nan"),1e6),))

    def test_boundary_residual_is_zero_only_on_demand_ray(self):
        ok=radial_boundary_alignment_residual(
            demand_m2=Moment.nmm(3),demand_m3=Moment.nmm(4),
            radius=100e6,boundary_m2=60e6,boundary_m3=80e6)
        self.assertAlmostEqual(ok.as_nmm,0.,delta=1e-8)
        bad=radial_boundary_alignment_residual(
            demand_m2=Moment.nmm(3),demand_m3=Moment.nmm(4),
            radius=100e6,boundary_m2=-60e6,boundary_m3=-80e6)
        self.assertGreater(bad.as_nmm,100e6)
        with self.assertRaises(ValueError):
            radial_boundary_alignment_residual(
                demand_m2=Moment.nmm(0),demand_m3=Moment.nmm(0),
                radius=1e6,boundary_m2=1e6,boundary_m3=0)

    def test_real_fixture_radial_hull_and_report_trace(self):
        p=fixture_problem(layout="B",angle_count=72,
            request=RadialCapacityAtAxialForce(
                Force.kn(500),Moment.kn_m(40),Moment.kn_m(20)))
        x=calculate_section(p)
        self.assertEqual(x.status,SectionStatus.COMPLETE_RADIAL,x.issues[:3])
        self.assertEqual(x.radial_hull_evidence.status,
                         RadialHullStatus.ORIGIN_STRICT_INTERIOR_SAMPLED)
        self.assertEqual(
            x.radial_hull_evidence.usable_direction_count+
            x.radial_hull_evidence.near_origin_point_count,72)
        self.assertGreater(x.radial_capacity.as_nmm,0.)
        self.assertLessEqual(
            x.radial_hull_evidence.boundary_alignment_residual.as_nmm,
            p.numerical_policy.moment_tol.as_nmm)
        j=json.loads(section_report_json(x))
        self.assertEqual(j["radial_hull"]["status"],
                         RadialHullStatus.ORIGIN_STRICT_INTERIOR_SAMPLED)
        self.assertIn("boundary_alignment_residual_nmm",j["radial_hull"])
        html=section_report_html(x)
        self.assertIn("Sampled radial-hull preflight",html)
        self.assertIn("ORIGIN_STRICT_INTERIOR_SAMPLED",html)

    def test_complete_status_cannot_be_forged_without_boundary_or_interior(self):
        p=fixture_problem(layout="B",angle_count=8,
            request=RadialCapacityAtAxialForce(
                Force.kn(500),Moment.kn_m(40),Moment.kn_m(20)))
        result=calculate_section(p)
        self.assertEqual(result.status,SectionStatus.COMPLETE_RADIAL,result.issues[:3])
        with self.assertRaises(ValueError):
            replace(result,radial_boundary_m3=None)
        with self.assertRaises(ValueError):
            replace(result,radial_capacity=None)
        with self.assertRaises(ValueError):
            replace(result,radial_hull_evidence=None)
        forged=replace(result.radial_hull_evidence,
            boundary_alignment_residual=Moment.nmm(1e9))
        with self.assertRaises(ValueError):
            replace(result,radial_hull_evidence=forged)

    def test_full_sample_population_outside_origin_must_not_call_kernel_ray(self):
        p=fixture_problem(layout="B",angle_count=8,
            request=RadialCapacityAtAxialForce(
                Force.kn(500),Moment.kn_m(40),Moment.kn_m(20)))
        def fake_scan(*args,**kwargs):
            return RootScanAudit(359,1,0,20.)
        def fake_solution(_adapter,angle,target,policy,material,bars):
            return SimpleNamespace(
                neutral_axis_angle_deg=angle.as_deg,
                neutral_axis_depth_c_mm=240.,
                n_compression_n=target.as_n,
                m2_nmm=10e6+10000.*angle.as_deg,
                m3_nmm=3e6+1000.*angle.as_deg,
            )
        with patch.object(SectionKernelAdapter,"sample_axial_brackets",
                          fake_scan),patch.object(
            SectionKernelAdapter,"solve_one",fake_solution
        ),patch.object(
            SectionKernelAdapter,"radial",
            side_effect=AssertionError("unsafe ray call")):
            result=calculate_section(p)
        self.assertEqual(result.status,SectionStatus.NUMERIC_UNRESOLVED)
        self.assertTrue(result.angular_coverage.is_complete)
        self.assertEqual(len(result.states),8)
        self.assertEqual(result.radial_hull_evidence.status,
                         RadialHullStatus.ORIGIN_NOT_INTERIOR_SAMPLED)
        self.assertIsNone(result.radial_capacity)
        self.assertIn("RADIAL_HULL:ORIGIN_NOT_INTERIOR_SAMPLED",result.issues)
        self.assertIsNone(json.loads(section_report_json(result))["radial_capacity_nmm"])

    def test_aligned_preflight_does_not_hide_bad_kernel_ray(self):
        p=fixture_problem(layout="B",angle_count=8,
            request=RadialCapacityAtAxialForce(
                Force.kn(500),Moment.kn_m(40),Moment.kn_m(20)))
        bad=SimpleNamespace(status="PROVEN",capacity_nmm=1e8,
                            boundary_m2_nmm=-1e8,boundary_m3_nmm=0.)
        with patch.object(SectionKernelAdapter,"radial",return_value=bad):
            result=calculate_section(p)
        self.assertEqual(result.status,SectionStatus.NUMERIC_UNRESOLVED)
        self.assertIn("RADIAL_BOUNDARY_MISALIGNED_WITH_DEMAND_RAY",
                      result.issues)
        self.assertIsNone(result.radial_capacity)
        self.assertEqual(result.radial_hull_evidence.status,
                         RadialHullStatus.ORIGIN_STRICT_INTERIOR_SAMPLED)
        self.assertIsNone(result.radial_hull_evidence.boundary_alignment_residual)


if __name__=="__main__":
    unittest.main()
