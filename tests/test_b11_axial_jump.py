"""B11: continuous finite-area bar overlap and fail-closed root regression."""
from math import cos, sin, radians
from unittest import TestCase
from examples.section_pilot import fixture_problem
from tbdy_column_core.domain.quantities import Angle, Force
from tbdy_column_core.engineering.section_adapter import SectionKernelAdapter


class B11AxialJumpTests(TestCase):
    def test_source_bar_entry_is_continuous_and_not_misclassified_as_jump(self):
        p=fixture_problem(layout="B",angle_count=8)
        adapter=SectionKernelAdapter(p.section,p.frame_model_contract)
        material=adapter.prepare_material()
        bars=adapter.bars()
        for theta in (0.0,33.0,90.0,137.0):
            nx,ny=cos(radians(theta)),sin(radians(theta))
            qext=(abs(nx)*p.section.profile.b.as_mm+
                  abs(ny)*p.section.profile.h.as_mm)/2
            cs=sorted(set((qext-(bar.x2_mm*nx+bar.x3_mm*ny))/material.k1
                          for bar in bars))
            for c in cs:
                if c<=1e-4:
                    continue
                before=adapter.evaluate(Angle.deg(theta),c-1e-5,material,bars).n_compression_n
                after=adapter.evaluate(Angle.deg(theta),c+1e-5,material,bars).n_compression_n
                self.assertLess(abs(after-before),5.0,(theta,c,before,after))
        audit=adapter.sample_axial_brackets(
            Angle.deg(0),Force.kn(500),material,bars,force_atol_n=1)
        self.assertEqual(audit.discovered_jump_crossings,0)
        self.assertTrue(audit.accepted_single_bracket)
        self.assertEqual(audit.issue_code,"")

    def test_reference_fixture_fixed_n_has_one_qualified_bracket(self):
        p=fixture_problem(layout="B",angle_count=8)
        adapter=SectionKernelAdapter(p.section,p.frame_model_contract)
        audit=adapter.sample_axial_brackets(Angle.deg(0),Force.kn(500),
                     adapter.prepare_material(),adapter.bars(),force_atol_n=1)
        self.assertEqual(audit.sign_brackets,1)
        self.assertEqual(audit.discovered_jump_crossings,0)
        self.assertTrue(audit.accepted_single_bracket)
