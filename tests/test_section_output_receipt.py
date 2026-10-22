"""B6 report output checksum: passive, deterministic, not a signature."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from unittest.mock import patch
import json
import unittest

from examples.section_pilot import fixture_problem
from tbdy_column_core.application.services import calculate_section
from tbdy_column_core.domain.quantities import Force, Moment
from tbdy_column_core.domain.section_requests import (
    EnvelopeAtAxialForce, RadialCapacityAtAxialForce, SectionStatus,
)
from tbdy_column_core.reporting.section_report import (
    section_report_json,section_report_html,section_payload,
)
from tbdy_column_core.reporting.section_receipt import (
    RECEIPT_SCHEMA,output_receipt_for_payload,verify_section_report_json,
)


class B6OutputReceiptTests(unittest.TestCase):
    def test_checksum_matches_canonical_numerical_payload(self):
        p=fixture_problem(layout="A")
        result=calculate_section(p)
        body=section_payload(result)
        receipt=body.pop("output_receipt")
        self.assertEqual(receipt["schema"],RECEIPT_SCHEMA)
        self.assertEqual(receipt["input_sha256"],result.input_fingerprint.sha256)
        encoded=json.dumps(body,sort_keys=True,ensure_ascii=False,
                           allow_nan=False,separators=(",",":")).encode("utf-8")
        self.assertEqual(receipt["sha256"],sha256(encoded).hexdigest())
        text=section_report_json(result)
        self.assertTrue(verify_section_report_json(text))
        self.assertIn(receipt["sha256"],section_report_html(result))
        self.assertEqual(text,section_report_json(calculate_section(p)))

    def test_same_input_different_calculated_state_produces_new_output_receipt(self):
        p=fixture_problem(layout="B")
        result=calculate_section(p)
        shifted=replace(result.states[0],
                        n=Force.n(result.states[0].n.as_n+1.0))
        other=replace(result,states=(shifted,))
        a=section_payload(result)
        b=section_payload(other)
        self.assertEqual(a["input_fingerprint"],b["input_fingerprint"])
        self.assertNotEqual(a["output_receipt"]["sha256"],b["output_receipt"]["sha256"])
        self.assertTrue(verify_section_report_json(section_report_json(other)))

    def test_status_issues_policy_and_coverage_all_bound(self):
        p=fixture_problem(layout="B",angle_count=8,
            request=EnvelopeAtAxialForce(Force.kn(500)))
        result=calculate_section(p)
        original=section_payload(result)
        self.assertEqual(result.status,SectionStatus.COMPLETE_ENVELOPE)
        raw={key:value for key,value in original.items() if key!="output_receipt"}
        for key,changed in (
            ("status","NUMERIC_UNRESOLVED"),
            ("issues",["ANGLE_0:NEW_WARNING"]),
            ("numeric_root_quality","CHANGED_ROOT_QUALITY"),
        ):
            candidate=json.loads(json.dumps(raw))
            candidate[key]=changed
            self.assertNotEqual(
                output_receipt_for_payload(candidate)["sha256"],
                original["output_receipt"]["sha256"])
        coverage=json.loads(json.dumps(raw))
        coverage["angular_coverage"]["missing_indices"]=[0]
        self.assertNotEqual(output_receipt_for_payload(coverage)["sha256"],
                            original["output_receipt"]["sha256"])
        policy=json.loads(json.dumps(raw))
        policy["applied_policy"]["max_iterations"]+=1
        self.assertNotEqual(output_receipt_for_payload(policy)["sha256"],
                            original["output_receipt"]["sha256"])

    def test_tampering_any_reported_result_or_source_is_detected(self):
        p=fixture_problem(layout="B")
        result=calculate_section(p)
        original=json.loads(section_report_json(result))
        for key,mutate in (
            ("n",lambda x:x["states"][0].__setitem__("n_n",123.0)),
            ("source",lambda x:x["input_refs"][0].__setitem__("input_revision","rev999")),
            ("input",lambda x:x["input_fingerprint"].__setitem__("sha256","1"*64)),
            ("section",lambda x:x["section_ref"].__setitem__("revision","stale")),
            ("issue",lambda x:x["issues"].append("UNREVIEWED")),
        ):
            with self.subTest(key=key):
                tampered=json.loads(json.dumps(original))
                mutate(tampered)
                self.assertFalse(verify_section_report_json(json.dumps(tampered)))

    def test_missing_invalid_duplicate_receipts_and_nan_fail_closed(self):
        p=fixture_problem()
        original=json.loads(section_report_json(calculate_section(p)))
        without={k:v for k,v in original.items() if k!="output_receipt"}
        self.assertFalse(verify_section_report_json(json.dumps(without)))
        wrong=json.loads(json.dumps(original))
        wrong["output_receipt"]["schema"]="unsupported"
        self.assertFalse(verify_section_report_json(json.dumps(wrong)))
        self.assertFalse(verify_section_report_json("not JSON"))
        self.assertFalse(verify_section_report_json("[]"))
        self.assertFalse(verify_section_report_json("null"))
        self.assertFalse(verify_section_report_json("{\"schema\":0,\"schema\":1}"))
        nan=json.loads(json.dumps(original))
        nan["states"][0]["n_n"]=float("nan")
        self.assertFalse(verify_section_report_json(json.dumps(nan)))
        self.assertFalse(verify_section_report_json(None))

    def test_reports_are_passive_and_not_physics_recomputed(self):
        p=fixture_problem()
        result=calculate_section(p)
        with patch("tbdy_column_core.physics.section_capacity.evaluate_rectangular_column_capacity_state",
                   side_effect=AssertionError("report must not recalculate section")):
            with patch("tbdy_column_core.engineering.input_identity.section_input_fingerprint",
                       side_effect=AssertionError("report must not rehash raw problem")):
                text=section_report_json(result)
                html=section_report_html(result)
                self.assertTrue(verify_section_report_json(text))
                self.assertIn(json.loads(text)["output_receipt"]["sha256"],html)

    def test_unresolved_unsupported_zero_radial_also_have_receipts(self):
        p=fixture_problem(layout="B",angle_count=8,max_iterations=1,
            request=EnvelopeAtAxialForce(Force.kn(500)))
        unsupported=replace(p,section=replace(p.section,
            longitudinal=replace(p.section.longitudinal,
                bars=(replace(p.section.longitudinal.bars[0],steel_ref="UNKNOWN"),)
                +p.section.longitudinal.bars[1:])))
        zero=replace(p,request=RadialCapacityAtAxialForce(
            Force.kn(500),Moment.nmm(0),Moment.nmm(0)))
        for item in (p,unsupported,zero):
            with self.subTest(kind=type(item.request).__name__,invalid=item is unsupported):
                result=calculate_section(item)
                self.assertNotEqual(result.status,SectionStatus.COMPLETE_RADIAL)
                document=section_report_json(result)
                self.assertTrue(verify_section_report_json(document))
                parsed=json.loads(document)
                self.assertEqual(parsed["output_receipt"]["input_sha256"],
                                 result.input_fingerprint.sha256)
                self.assertFalse(parsed["full_column_design_pass"])

    def test_recomputed_unsigned_checksum_does_not_authenticate_source(self):
        # Deliberately show threat boundary: anyone can calculate a SHA-256.
        result=calculate_section(fixture_problem())
        original=json.loads(section_report_json(result))
        original["source_tampered_note"]="an external actor added this field"
        altered={k:v for k,v in original.items() if k!="output_receipt"}
        self.assertFalse(verify_section_report_json(json.dumps(original)))
        original["output_receipt"]=output_receipt_for_payload(altered)
        self.assertTrue(verify_section_report_json(json.dumps(original)))
        self.assertIn("unsigned",original["output_receipt"]["meaning"])


if __name__=="__main__":
    unittest.main()
