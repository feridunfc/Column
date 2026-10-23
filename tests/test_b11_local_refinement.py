"""B11 local demand-ray refinement: measurements not a global certificate."""
import unittest
from examples.section_pilot import fixture_problem
from tbdy_column_core.domain.section_requests import RadialCapacityAtAxialForce
from tbdy_column_core.domain.quantities import Force,Moment
from tbdy_column_core.engineering.local_refinement import (
    assess_local_radial_refinement,LocalRefinementStatus)


class LocalRefinementTests(unittest.TestCase):
    def test_actual_400x600_fixed_n_local_angles_measured(self):
        p=fixture_problem(layout="B",angle_count=72,
            request=RadialCapacityAtAxialForce(Force.kn(500),Moment.kn_m(40),Moment.kn_m(20)))
        out=assess_local_radial_refinement(p,max_added_angles=12)
        self.assertEqual(out.base_angle_count,72)
        self.assertTrue(out.capacity_history_nmm)
        self.assertEqual(len(out.added_angles_deg),len(out.differences_nmm))
        self.assertIn(out.status,(LocalRefinementStatus.OBSERVED_LOCAL_STABLE,
                                  LocalRefinementStatus.OBSERVED_LOCAL_NOT_STABLE,
                                  LocalRefinementStatus.NUMERIC_UNRESOLVED))
        self.assertIn("NOT a rigorous bound",out.interpretation)
        if out.status==LocalRefinementStatus.OBSERVED_LOCAL_STABLE:
            self.assertLessEqual(out.differences_nmm[-1],out.budget_nmm)
            self.assertLessEqual(out.differences_nmm[-2],out.budget_nmm)
            self.assertFalse(out.issues)

    def test_requires_typed_radial_and_two_refinements(self):
        p=fixture_problem()
        with self.assertRaises(TypeError):
            assess_local_radial_refinement(p)
        with self.assertRaises(ValueError):
            assess_local_radial_refinement(p,max_added_angles=1)
