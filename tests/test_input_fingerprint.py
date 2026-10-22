"""B5: input fingerprint is a deterministic identity, not approval evidence."""
from __future__ import annotations
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from examples.section_pilot import fixture_problem
from tbdy_column_core.application.services import calculate_section
from tbdy_column_core.domain.identity import EvidenceRef,RevisionRef,SourceRef
from tbdy_column_core.domain.quantities import Angle,Force,Length,Moment,Stress
from tbdy_column_core.domain.section_requests import (
    AtStrainState,EnvelopeAtAxialForce,RadialCapacityAtAxialForce,
    CalculationInputFingerprint,
)
from tbdy_column_core.engineering.input_identity import section_input_fingerprint
from tbdy_column_core.engineering.section_solver import KERNEL_REF
from tbdy_column_core.reporting.section_report import section_report_html,section_report_json


def digest(problem):
    return section_input_fingerprint(problem,kernel_ref=KERNEL_REF).sha256


class B5InputFingerprintTests(unittest.TestCase):
    def test_deterministic_repetition_matches_result_json_html(self):
        p=fixture_problem(layout="B")
        result=calculate_section(p)
        self.assertEqual(result.input_fingerprint.sha256,digest(p))
        self.assertEqual(result.input_fingerprint.schema,
                         CalculationInputFingerprint.SCHEMA)
        self.assertEqual(result.input_fingerprint.sha256,calculate_section(p).input_fingerprint.sha256)
        payload=json.loads(section_report_json(result))
        self.assertEqual(payload["input_fingerprint"]["sha256"],digest(p))
        self.assertEqual(payload["input_fingerprint"]["schema"],
                         CalculationInputFingerprint.SCHEMA)
        self.assertIn(digest(p),section_report_html(result))
        self.assertFalse(payload["full_column_design_pass"])

    def test_unit_equivalence_and_rebar_order_do_not_change_digest(self):
        p=fixture_problem(layout="B",units="mm")
        q=fixture_problem(layout="B",units="cm")
        self.assertEqual(digest(p),digest(q))
        cage=p.section.longitudinal
        reordered=replace(p,section=replace(p.section,
            longitudinal=replace(cage,bars=tuple(reversed(cage.bars)))))
        self.assertEqual(digest(p),digest(reordered))

    def test_reordered_evidence_refs_do_not_change_digest(self):
        p=fixture_problem()
        other=EvidenceRef("ANOTHER",
            SourceRef("MANUAL","other_fixture","record-2","mm","offline2"),
            RevisionRef("source","other","rev2"))
        a=replace(p,input_refs=p.input_refs+(other,))
        b=replace(p,input_refs=(other,)+p.input_refs)
        self.assertEqual(digest(a),digest(b))
        self.assertNotEqual(digest(p),digest(a))

    def test_same_section_revision_cannot_hide_changed_rebar_geometry_or_material(self):
        p=fixture_problem(layout="B")
        bar=p.section.longitudinal.bars[0]
        relocated=replace(bar,x2=Length.mm(bar.x2.as_mm+5))
        cage=replace(p.section.longitudinal,
                     bars=(relocated,)+p.section.longitudinal.bars[1:])
        changed_bar=replace(p,section=replace(p.section,longitudinal=cage))
        self.assertEqual(changed_bar.section.ref,p.section.ref)
        self.assertNotEqual(digest(changed_bar),digest(p))
        steel=p.section.material.steel_laws[0]
        law=replace(steel,fyd=Stress.mpa(steel.fyd.as_mpa+2))
        material=replace(p.section.material,steel_laws=(law,))
        changed_law=replace(p,section=replace(p.section,material=material))
        self.assertEqual(changed_law.section.ref,p.section.ref)
        self.assertNotEqual(digest(changed_law),digest(p))
        changed_shape=replace(p,section=replace(p.section,
            profile=replace(p.section.profile,h=Length.mm(610))))
        self.assertNotEqual(digest(changed_shape),digest(p))

    def test_request_policy_frame_and_declared_source_bind_distinctly(self):
        p=fixture_problem(layout="B")
        variants=(
            replace(p,request=AtStrainState(Angle.deg(34),Length.mm(240))),
            replace(p,request=EnvelopeAtAxialForce(Force.kn(500))),
            replace(p,request=RadialCapacityAtAxialForce(
                Force.kn(500),Moment.kn_m(40),Moment.kn_m(20))),
            replace(p,numerical_policy=replace(p.numerical_policy,angle_count=144)),
            replace(p,numerical_policy=replace(p.numerical_policy,max_iterations=101)),
            replace(p,frame_model_contract=replace(
                p.frame_model_contract,reference="CUSTOM_FRAME_REFERENCE")),
            replace(p,input_refs=(replace(p.input_refs[0],
                input_revision=RevisionRef("source","synthetic","rev2")),)),
        )
        first=digest(p)
        for v in variants:
            with self.subTest(request=type(v.request).__name__,variant=repr(v)[:70]):
                self.assertNotEqual(first,digest(v))

    def test_no_fingerprint_forgery_and_no_kernel_recompute_in_reports(self):
        p=fixture_problem(layout="B")
        result=calculate_section(p)
        with self.assertRaises(TypeError):
            replace(result,input_fingerprint="not-a-typed-identity")
        with self.assertRaises(ValueError):
            CalculationInputFingerprint(CalculationInputFingerprint.SCHEMA,"0"*63)
        with self.assertRaises(ValueError):
            CalculationInputFingerprint("unsupported-schema","0"*64)
        with patch("tbdy_column_core.engineering.input_identity.section_input_fingerprint",
                   side_effect=AssertionError("report must not fingerprint source")):
            self.assertIn(digest(p),section_report_json(result))
            self.assertIn(digest(p),section_report_html(result))

    def test_unresolved_and_undefined_results_retain_declared_input_identity(self):
        p=fixture_problem(layout="B",angle_count=8,max_iterations=1,
            request=EnvelopeAtAxialForce(Force.kn(500)))
        unresolved=calculate_section(p)
        self.assertEqual(unresolved.input_fingerprint.sha256,digest(p))
        self.assertIn(digest(p),section_report_json(unresolved))
        undefined=replace(p,request=RadialCapacityAtAxialForce(
            Force.kn(500),Moment.nmm(0),Moment.nmm(0)))
        result=calculate_section(undefined)
        self.assertEqual(result.input_fingerprint.sha256,digest(undefined))
        self.assertNotEqual(result.input_fingerprint.sha256,unresolved.input_fingerprint.sha256)


if __name__=="__main__":
    unittest.main()
