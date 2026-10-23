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

    def test_concrete_block_bar_overlap_is_continuous_and_axial_response_monotone(self):
        from math import cos, sin, radians
        from tbdy_column_core.engineering.section_adapter import SectionKernelAdapter
        p=fixture_problem(layout="B",angle_count=8)
        adapter=SectionKernelAdapter(p.section,p.frame_model_contract)
        material=adapter.prepare_material()
        bars=adapter.bars()
        width=p.section.profile.b.as_mm
        depth=p.section.profile.h.as_mm
        for theta in (0.0,33.0,90.0,137.0):
            nx,ny=cos(radians(theta)),sin(radians(theta))
            extreme=(abs(nx)*width+abs(ny)*depth)/2
            transition_cs=tuple((extreme-(bar.x2_mm*nx+bar.x3_mm*ny))/material.k1
                                for bar in bars)
            for c in transition_cs:
                if c<=1e-4:
                    continue
                gap=1e-5
                left=adapter.evaluate(Angle.deg(theta),c-gap,material,bars)
                right=adapter.evaluate(Angle.deg(theta),c+gap,material,bars)
                self.assertLess(abs(right.n_compression_n-left.n_compression_n),5.0)
            diagonal=(width*width+depth*depth)**.5
            samples=(max(diagonal*1e-6,1e-6),diagonal*1e-3,diagonal*1e-1,
                     diagonal,diagonal*1e2,diagonal*1e4)
            axial=[adapter.evaluate(Angle.deg(theta),c,material,bars).n_compression_n
                   for c in samples]
            self.assertTrue(all(a<=b+1e-6 for a,b in zip(axial,axial[1:])),axial)

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
            self.assertTrue(result.angular_coverage.is_complete,result.issues[:4])
            self.assertEqual(result.angular_coverage.missing_indices,())
            self.assertEqual(len(result.states),count)
            self.assertIsNotNone(result.radial_capacity)
            radii.append(result.radial_capacity.as_nmm)
            self.assertFalse(result.full_column_design_pass)
        self.assertLess(abs(radii[0]-radii[1]),.03*radii[1])
        p=fixture_problem(layout="B")
        bars,material=oracle_fixture(p)
        oracle=radial_capacity_dense_convex(
            width_mm=400,depth_mm=600,bars=bars,material=material,
            target_n=500000,demand_m2_nmm=40000000,demand_m3_nmm=20000000,
            angle_count=144,root_scan_count=160,axial_tolerance_n=1,
        )
        self.assertEqual(oracle.status,"PROVEN")
        self.assertAlmostEqual(radii[1],oracle.capacity_nmm,
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


    def test_zero_radial_direction_does_not_execute_scan(self):
        from unittest.mock import patch
        from tbdy_column_core.engineering.section_adapter import SectionKernelAdapter
        p=fixture_problem(angle_count=8,request=RadialCapacityAtAxialForce(
            Force.kn(500),Moment.nmm(0),Moment.nmm(0)))
        with patch.object(SectionKernelAdapter,"sample_axial_brackets",
                          side_effect=AssertionError("unnecessary scan")):
            out=calculate_section(p)
        self.assertEqual(out.status,SectionStatus.UNDEFINED_MOMENT_DIRECTION)
        self.assertIsNone(out.angle_step)
        self.assertEqual(out.root_quality,"NOT_APPLICABLE_ZERO_DIRECTION")

    def test_dual_density_scan_carries_true_sampling_evidence(self):
        p=fixture_problem(angle_count=8,
            request=EnvelopeAtAxialForce(Force.kn(500)))
        out=calculate_section(p)
        self.assertEqual(out.status,SectionStatus.COMPLETE_ENVELOPE,out.issues[:4])
        self.assertEqual(out.root_quality,
                         "CONTINUOUS_MONOTONE_AXIAL_MODEL_SINGLE_BRACKET_CHECK")
        for state in out.states:
            self.assertEqual(state.root_scan_samples,359)
            self.assertEqual(state.sampled_root_brackets,1)
            self.assertGreaterEqual(state.root_min_abs_residual.as_n,0)
        payload=json.loads(section_report_json(out))
        self.assertEqual(payload["states"][0]["root_scan_samples"],359)
        self.assertIn("root_min_abs_residual_n",section_report_html(out))

    def test_multiple_and_near_tangent_roots_fail_closed(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from math import log
        from tbdy_column_core.engineering.section_adapter import SectionKernelAdapter
        p=fixture_problem(angle_count=8,request=EnvelopeAtAxialForce(Force.n(0)))
        a=SectionKernelAdapter(p.section,p.frame_model_contract)
        material=a.prepare_material()
        bars=a.bars()
        # Log c across the source scan range. Synthetic root profile is
        # strictly a test double; it never enters the production math kernel.
        d=(p.section.profile.b.as_mm**2+p.section.profile.h.as_mm**2)**.5
        c0=max(d*1e-6,1e-6)
        c1=d*1e4
        def multi(_self,angle,c,material,bars):
            x=log(c/c0)/log(c1/c0)
            return SimpleNamespace(n_compression_n=(x-.22)*(x-.79)*1e6)
        with patch.object(SectionKernelAdapter,"evaluate",multi):
            aud=a.sample_axial_brackets(Angle.deg(0),Force.n(0),material,bars,
                                       force_atol_n=1.)
            self.assertGreaterEqual(aud.sign_brackets,2)
            self.assertFalse(aud.accepted_single_bracket)
            self.assertEqual(aud.issue_code,"MULTIPLE_SAMPLED_ROOT_BRACKETS")
        # Exact tangency at one of 359 log samples, with no sign crossing.
        xhit=179/358
        def tangent(_self,angle,c,material,bars):
            x=log(c/c0)/log(c1/c0)
            return SimpleNamespace(n_compression_n=(x-xhit)**2*1e8)
        with patch.object(SectionKernelAdapter,"evaluate",tangent):
            aud=a.sample_axial_brackets(Angle.deg(0),Force.n(0),material,bars,
                                       force_atol_n=1.)
            self.assertEqual(aud.sign_brackets,0)
            self.assertGreater(aud.near_zero_samples,0)
            self.assertEqual(aud.issue_code,"NEAR_ZERO_WITHOUT_SIGN_BRACKET")


    def test_angular_budget_is_separate_from_axial_residual(self):
        from tbdy_column_core.engineering.convergence import (
            assess_radial_angular_refinement,AngularRefinementStatus,
        )
        p=fixture_problem(layout="B",angle_count=8,
            request=RadialCapacityAtAxialForce(
                Force.kn(500),Moment.kn_m(40),Moment.kn_m(20)))
        diag=assess_radial_angular_refinement(p)
        a=calculate_section(p)
        fine=calculate_section(replace(
            p,numerical_policy=replace(p.numerical_policy,angle_count=16)))
        self.assertEqual(diag.coarse_angle_count,8)
        self.assertEqual(diag.fine_angle_count,16)
        self.assertIn(diag.status,(
            AngularRefinementStatus.OBSERVED_DELTA_WITHIN_BUDGET,
            AngularRefinementStatus.OBSERVED_DELTA_EXCEEDS_BUDGET))
        self.assertAlmostEqual(diag.coarse_capacity.as_nmm,
                               a.radial_capacity.as_nmm,delta=1e-8)
        self.assertAlmostEqual(diag.fine_capacity.as_nmm,
                               fine.radial_capacity.as_nmm,delta=1e-8)
        self.assertAlmostEqual(diag.observed_delta.as_nmm,
                               abs(diag.fine_capacity.as_nmm-diag.coarse_capacity.as_nmm),
                               delta=1e-8)
        self.assertAlmostEqual(diag.numeric_budget.as_nmm,p.numerical_policy.moment_tol.as_nmm)
        self.assertIn("not a certified",diag.interpretation)

    def test_angular_refinement_unresolved_on_root_failure(self):
        from tbdy_column_core.engineering.convergence import (
            assess_radial_angular_refinement,AngularRefinementStatus,
        )
        p=fixture_problem(layout="B",angle_count=8,max_iterations=1,
            request=RadialCapacityAtAxialForce(
                Force.kn(500),Moment.kn_m(40),Moment.kn_m(20)))
        diag=assess_radial_angular_refinement(p)
        self.assertEqual(diag.status,AngularRefinementStatus.UNRESOLVED)
        self.assertIsNone(diag.observed_delta)
        self.assertIn("INCOMPLETE_NUMERICAL_CAPACITY",diag.issues)



    def test_b3_angular_coverage_exact_and_partial(self):
        from unittest.mock import patch
        from tbdy_column_core.domain.section_requests import AngularCoverage
        from tbdy_column_core.engineering.section_adapter import SectionKernelAdapter
        p=fixture_problem(layout="B",angle_count=8,
            request=EnvelopeAtAxialForce(Force.kn(500)))
        full=calculate_section(p)
        self.assertTrue(full.angular_coverage.is_complete)
        self.assertEqual(full.angular_coverage.resolved_indices,tuple(range(8)))
        self.assertEqual(full.angular_coverage.missing_indices,())
        raw=json.loads(section_report_json(full))
        self.assertEqual(raw["angular_coverage"]["attempted_count"],8)
        self.assertTrue(raw["angular_coverage"]["complete"])
        original=SectionKernelAdapter.sample_axial_brackets
        def fail_one(adapter, angle, target, material, bars, *, force_atol_n):
            if angle.as_deg==45.:
                raise ValueError("synthetic angle interruption")
            return original(adapter,angle,target,material,bars,
                            force_atol_n=force_atol_n)
        with patch.object(SectionKernelAdapter,"sample_axial_brackets",fail_one):
            partial=calculate_section(p)
        self.assertEqual(partial.status,SectionStatus.PARTIAL_ENVELOPE)
        self.assertEqual(partial.angular_coverage.missing_indices,(1,))
        self.assertEqual(len(partial.states),7)
        parsed=json.loads(section_report_json(partial))
        self.assertEqual(parsed["angular_coverage"]["missing_indices"],[1])
        self.assertIn("Missing: [1]",section_report_html(partial))
        self.assertFalse(partial.full_column_design_pass)
        with self.assertRaises(ValueError):
            AngularCoverage(8,(0,1),(1,2,3,4,5,6,7))
        with self.assertRaises(ValueError):
            replace(full,angular_coverage=partial.angular_coverage)

    def test_b3_public_checked_boundary_and_programmer_errors(self):
        from tbdy_column_core.application.services import (
            validate_section_problem,calculate_section_validated,ValidationStatus)
        p=fixture_problem()
        invalid=calculate_section_validated({"section":p.section})
        self.assertEqual(invalid.validation.status,ValidationStatus.INVALID_INPUT)
        self.assertIsNone(invalid.result)
        valid=calculate_section_validated(p)
        self.assertEqual(valid.validation.status,ValidationStatus.READY)
        self.assertEqual(valid.result,calculate_section(p))
        self.assertEqual(valid.result.status,SectionStatus.NUMERIC_STATE)
        bad_frame=replace(p.frame_model_contract,reference="UNSUPPORTED_OFFSET")
        bad=calculate_section_validated(replace(p,frame_model_contract=bad_frame))
        self.assertEqual(bad.validation.status,ValidationStatus.UNSUPPORTED_INPUT)
        self.assertIsNone(bad.result)
        with self.assertRaises(TypeError):
            calculate_section({"section":p.section})

    def test_b3_unsupported_material_has_no_angular_coverage(self):
        from tbdy_column_core.application.services import (
            calculate_section_validated, ValidationStatus,
        )
        p=fixture_problem(layout="B",angle_count=8,
            request=EnvelopeAtAxialForce(Force.kn(500)))
        bar=replace(p.section.longitudinal.bars[0],steel_ref="UNKNOWN")
        layout=replace(p.section.longitudinal,
            bars=(bar,)+p.section.longitudinal.bars[1:])
        altered=replace(p,section=replace(p.section,longitudinal=layout))
        raw=calculate_section(altered)
        self.assertEqual(raw.status,SectionStatus.UNSUPPORTED_MATERIAL)
        self.assertIsNone(raw.angular_coverage)
        validated=calculate_section_validated(altered)
        self.assertEqual(validated.validation.status,ValidationStatus.UNSUPPORTED_INPUT)
        self.assertIsNone(validated.result)

    def test_b3_axial_sign_mismatch_rejected_not_assumed(self):
        from tbdy_column_core.domain.coordinates import AxialSignConvention
        from tbdy_column_core.application.services import (
            calculate_section_validated,ValidationStatus,
        )
        p=fixture_problem()
        wrong=replace(p,frame_model_contract=replace(
            p.frame_model_contract,axial_sign=AxialSignConvention.F1_TENSION_POSITIVE))
        validated=calculate_section_validated(wrong)
        self.assertEqual(validated.validation.status,ValidationStatus.UNSUPPORTED_INPUT)
        with self.assertRaisesRegex(ValueError,"UNSUPPORTED_AXIAL_SIGN_CONVENTION"):
            calculate_section(wrong)

    def test_b3_input_source_revision_propagates_to_both_reports(self):
        p=fixture_problem()
        result=calculate_section(p)
        parsed=json.loads(section_report_json(result))
        ref=parsed["input_refs"][0]
        self.assertEqual(ref["producer"],p.input_refs[0].source.producer)
        self.assertEqual(ref["declared_units"],p.input_refs[0].source.declared_units)
        self.assertEqual(ref["input_identifier"],p.input_refs[0].input_revision.identifier)
        html=section_report_html(result)
        for val in ("source_identifier","declared_units","acquisition_ref",
                    "input_identifier",str(parsed["section_ref"]["id"])):
            self.assertIn(val,html)


    def test_b4_local_frame_metadata_and_global_rigid_transform(self):
        from tbdy_column_core.domain.coordinates import Point3D,LocalFrame
        from tbdy_column_core.domain.quantities import Length
        p=fixture_problem(layout="B",request=AtStrainState(
            Angle.deg(33),Length.mm(240)))
        regular=calculate_section(p)
        rotated=LocalFrame(
            Point3D(Length.mm(1500),Length.mm(-200),Length.mm(800)),
            (1.,0.,0.),(0.,0.,1.),(0.,-1.,0.)
        )
        moved=replace(p,frame_model_contract=replace(
            p.frame_model_contract,frame=rotated))
        result=calculate_section(moved)
        # Given bars/moments are section-local; changing only the global
        # placement/orientation must not be treated as changing local physics.
        self.assertEqual(result.states,regular.states)
        payload=json.loads(section_report_json(result))
        self.assertEqual(payload["frame_model"]["origin_mm"],[1500.,-200.,800.])
        self.assertEqual(payload["frame_model"]["e2"],[0.,0.,1.])
        self.assertEqual(payload["frame_model"]["axial_sign"],"F1_COMPRESSION_POSITIVE")
        self.assertEqual(payload["frame_model"]["basis_max_residual"],0.)
        html=section_report_html(result)
        self.assertIn("origin_mm",html)
        self.assertIn("F1_COMPRESSION_POSITIVE",html)

    def test_b4_stricter_numeric_axis_policy_fails_closed(self):
        from math import sqrt
        from tbdy_column_core.domain.coordinates import Point3D,LocalFrame
        from tbdy_column_core.application.services import (
            calculate_section_validated,ValidationStatus,
        )
        from tbdy_column_core.domain.quantities import Length
        p=fixture_problem()
        frame=LocalFrame(
            Point3D(Length.mm(0),Length.mm(0),Length.mm(0)),
            (1.,0.,0.),(1e-6,sqrt(1.-1e-12),0.),(0.,0.,1.),
            axis_tolerance=1e-4,
        )
        problem=replace(p,frame_model_contract=replace(
            p.frame_model_contract,frame=frame))
        validated=calculate_section_validated(problem)
        self.assertEqual(validated.validation.status,ValidationStatus.INVALID_INPUT)
        self.assertIn("FRAME_EXCEEDS_REQUESTED_AXIS_TOLERANCE",
                      validated.validation.issues)
        self.assertIsNone(validated.result)
        with self.assertRaisesRegex(ValueError,"FRAME_EXCEEDS_REQUESTED_AXIS_TOLERANCE"):
            calculate_section(problem)
        # The policy is explicitly supplied; changing only that policy is
        # visible in the result, and the source frame is still immutable.
        relaxed=replace(problem,numerical_policy=replace(
            p.numerical_policy,axis_tol=1e-4))
        accepted=calculate_section(relaxed)
        self.assertGreater(accepted.frame_basis_max_residual,1e-10)
        self.assertLess(accepted.frame_basis_max_residual,relaxed.numerical_policy.axis_tol)

    def test_b4_frame_record_also_retained_for_unresolved_numeric_result(self):
        p=fixture_problem(angle_count=8,max_iterations=1,
            request=EnvelopeAtAxialForce(Force.kn(500)))
        result=calculate_section(p)
        self.assertIn(result.status,(SectionStatus.PARTIAL_ENVELOPE,
                                    SectionStatus.NUMERIC_UNRESOLVED))
        parsed=json.loads(section_report_json(result))
        self.assertEqual(parsed["frame_model"]["reference"],
                         "SECTION_GEOMETRIC_CENTROID")
        self.assertEqual(parsed["frame_model"]["requested_axis_tolerance"],
                         p.numerical_policy.axis_tol)


    def test_b6_source_root_must_match_observed_single_bracket(self):
        from unittest.mock import patch
        from dataclasses import replace as dc_replace
        from tbdy_column_core.engineering.section_adapter import SectionKernelAdapter
        p=fixture_problem(layout="B",angle_count=8,
            request=EnvelopeAtAxialForce(Force.kn(500)))
        ok=calculate_section(p)
        self.assertEqual(ok.status,SectionStatus.COMPLETE_ENVELOPE,ok.issues)
        original=SectionKernelAdapter.solve_one
        def switch_depth(adapter,angle,target,policy,material,bars):
            actual=original(adapter,angle,target,policy,material,bars)
            if actual is None:
                return None
            # Intentionally fake a source result with a physically inconsistent
            # c but perfectly matching N. Detection cannot rely on N alone.
            return dc_replace(actual,neutral_axis_depth_c_mm=1e10,
                              n_compression_n=target.as_n)
        with patch.object(SectionKernelAdapter,"solve_one",switch_depth):
            suspicious=calculate_section(p)
        self.assertEqual(suspicious.status,SectionStatus.NUMERIC_UNRESOLVED)
        self.assertIsNone(suspicious.radial_capacity)
        self.assertEqual(suspicious.angular_coverage.missing_indices,tuple(range(8)))
        self.assertTrue(all("ROOT_OUTSIDE_SAMPLED_BRACKET" in i
                            for i in suspicious.issues))

    def test_b6_three_level_observed_deltas_and_failure(self):
        from tbdy_column_core.engineering.triple_convergence import (
            assess_three_level_radial_refinement,TripleRefinementStatus)
        p=fixture_problem(layout="B",angle_count=8,
            request=RadialCapacityAtAxialForce(
                Force.kn(500),Moment.kn_m(40),Moment.kn_m(20)))
        outcome=assess_three_level_radial_refinement(p,counts=(8,16,32))
        self.assertEqual(outcome.counts,(8,16,32))
        self.assertNotEqual(outcome.verdict,TripleRefinementStatus.NUMERIC_UNRESOLVED,
                            outcome.issues)
        self.assertAlmostEqual(outcome.differences_nmm[0],
                               abs(outcome.capacity_nmm[1]-outcome.capacity_nmm[0]))
        self.assertAlmostEqual(outcome.differences_nmm[1],
                               abs(outcome.capacity_nmm[2]-outcome.capacity_nmm[1]))
        self.assertIn("not a rigorous bound",outcome.interpretation)
        with self.assertRaises(ValueError):
            assess_three_level_radial_refinement(p,counts=(8,8,16))
        p_fail=replace(p,numerical_policy=replace(
            p.numerical_policy,max_iterations=1))
        failed=assess_three_level_radial_refinement(p_fail,counts=(8,16,32))
        self.assertEqual(failed.verdict,TripleRefinementStatus.NUMERIC_UNRESOLVED)
        self.assertIn(None,failed.capacity_nmm)

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
