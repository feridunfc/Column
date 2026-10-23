"""B11: fail-closed axial discontinuity regression, not global-root proof."""
from unittest import TestCase
from examples.section_pilot import fixture_problem
from tbdy_column_core.domain.quantities import Angle, Force
from tbdy_column_core.engineering.section_adapter import SectionKernelAdapter


class B11AxialJumpTests(TestCase):
    def test_source_bar_entry_creates_jump_and_refuses_sign_only_root(self):
        p=fixture_problem(layout="B",angle_count=8)
        adapter=SectionKernelAdapter(p.section,p.frame_model_contract)
        material=adapter.prepare_material()
        bars=adapter.bars()
        angle=Angle.deg(0)
        qext=p.section.profile.b.as_mm/2
        cs=sorted(set((qext-bar.x2_mm)/material.k1 for bar in bars))
        pairs=[]
        for c in cs:
            if c<=0:
                continue
            before=adapter.evaluate(angle,c-1e-5,material,bars).n_compression_n
            after=adapter.evaluate(angle,c+1e-5,material,bars).n_compression_n
            if before-after>1000:
                pairs.append((c,before,after))
        self.assertTrue(pairs,"actual pinned physics has no demonstrable block-entry jump")
        c,left,right=pairs[0]
        target=Force.n((left+right)/2)
        audit=adapter.sample_axial_brackets(angle,target,material,bars,force_atol_n=1)
        self.assertGreater(audit.discovered_jump_crossings,0)
        self.assertFalse(audit.accepted_single_bracket)
        self.assertEqual(audit.issue_code,"AXIAL_JUMP_CROSSES_TARGET")
        self.assertTrue(any(abs(v-c)<1e-6 for v in audit.jump_depths_mm))

    def test_reference_fixture_fixed_n_no_spurious_jump_rejection(self):
        p=fixture_problem(layout="B",angle_count=8)
        adapter=SectionKernelAdapter(p.section,p.frame_model_contract)
        audit=adapter.sample_axial_brackets(Angle.deg(0),Force.kn(500),
                     adapter.prepare_material(),adapter.bars(),force_atol_n=1)
        self.assertEqual(audit.discovered_jump_crossings,0)
        self.assertTrue(audit.accepted_single_bracket)
