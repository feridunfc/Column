"""B10: candidate radial-origin safeguard ported from divergent B5.
These tests are engineering regression candidates; NOT Supervisor G2 approval.
"""
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch
import json
import unittest

from examples.section_pilot import fixture_problem
from tbdy_column_core.application.services import calculate_section
from tbdy_column_core.domain.quantities import Force, Moment
from tbdy_column_core.domain.section_requests import (
    SectionStatus, RadialCapacityAtAxialForce, RadialReferenceStatus,
)
from tbdy_column_core.engineering.section_adapter import SectionKernelAdapter, RootScanAudit
from tbdy_column_core.engineering.radial_admissibility import (
    check_radial_reference, verify_radial_boundary,
)
from tbdy_column_core.reporting.section_report import section_report_json,section_report_html


class RadialAdmissibilityB10(unittest.TestCase):
    def setUp(self):
        self.problem=fixture_problem(layout="B",angle_count=8,
            request=RadialCapacityAtAxialForce(Force.kn(500),Moment.kn_m(40),Moment.kn_m(20)))
        self.policy=self.problem.numerical_policy

    def test_quadrant_triangle_origin_outside(self):
        samples=[SimpleNamespace(m2_nmm=x,m3_nmm=y)
                 for x,y in ((10,10),(20,10),(10,20))]
        checked=check_radial_reference(samples,self.policy)
        self.assertEqual(checked.audit.status,RadialReferenceStatus.ORIGIN_NOT_STRICT_INTERIOR)
        self.assertLess(checked.audit.minimum_signed_origin_clearance.as_nmm,0)

    def test_origin_inside_and_edge_rejected(self):
        valid=[SimpleNamespace(m2_nmm=x,m3_nmm=y)
               for x,y in ((-10000,-10000),(10000,-10000),(10000,10000),(-10000,10000))]
        self.assertEqual(check_radial_reference(valid,self.policy).audit.status,
                         RadialReferenceStatus.VALIDATED)
        edge=[SimpleNamespace(m2_nmm=x,m3_nmm=y)
              for x,y in ((0,0),(10000,0),(10000,10000),(0,10000))]
        self.assertNotEqual(check_radial_reference(edge,self.policy).audit.status,
                            RadialReferenceStatus.VALIDATED)

    def test_outside_origin_public_solver_never_calls_radial(self):
        synthetic=SimpleNamespace(neutral_axis_angle_deg=0.,neutral_axis_depth_c_mm=200.,
            n_compression_n=500000.,m2_nmm=10_000_000.,m3_nmm=20_000_000.)
        audit=RootScanAudit(359,1,0,0.,((100.,300.),))
        with patch.object(SectionKernelAdapter,"sample_axial_brackets",return_value=audit), \
             patch.object(SectionKernelAdapter,"solve_one",return_value=synthetic), \
             patch.object(SectionKernelAdapter,"radial",side_effect=AssertionError("must not call")):
            actual=calculate_section(self.problem)
        self.assertEqual(actual.status,SectionStatus.NUMERIC_UNRESOLVED)
        self.assertIsNone(actual.radial_capacity)
        self.assertEqual(len(actual.states),8)
        self.assertEqual(actual.radial_reference_audit.status,
                         RadialReferenceStatus.DEGENERATE_SAMPLED_HULL)
        payload=json.loads(section_report_json(actual))
        self.assertIsNone(payload["radial_capacity_nmm"])
        self.assertIn("radial_reference_audit",section_report_html(actual))

    def test_real_fixture_and_forged_result(self):
        actual=calculate_section(self.problem)
        self.assertEqual(actual.status,SectionStatus.COMPLETE_RADIAL,actual.issues[:4])
        self.assertEqual(actual.radial_reference_audit.status,RadialReferenceStatus.VALIDATED)
        payload=json.loads(section_report_json(actual))
        self.assertEqual(payload["radial_reference_audit"]["status"],"VALIDATED")
        self.assertIn("VALIDATED",section_report_html(actual))
        with self.assertRaises(ValueError):
            replace(actual,radial_reference_audit=None)
        with self.assertRaises(ValueError):
            replace(actual,radial_capacity=None)

    def test_boundary_consistency_rejects_wrong_positive_ray(self):
        samples=[SimpleNamespace(m2_nmm=x,m3_nmm=y)
                 for x,y in ((-10000,-10000),(10000,-10000),(10000,10000),(-10000,10000))]
        hull=check_radial_reference(samples,self.policy)
        wrong=SimpleNamespace(status="PROVEN",capacity_nmm=10000.,
                              boundary_m2_nmm=-10000.,boundary_m3_nmm=0.)
        self.assertFalse(verify_radial_boundary(wrong,Moment.nmm(1),Moment.nmm(0),
                                                self.policy,hull))
        right=SimpleNamespace(status="PROVEN",capacity_nmm=10000.,
                              boundary_m2_nmm=10000.,boundary_m3_nmm=0.)
        self.assertTrue(verify_radial_boundary(right,Moment.nmm(1),Moment.nmm(0),
                                               self.policy,hull))
