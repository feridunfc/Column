"""B6 unsigned result receipt — payload, issue, numeric and link integrity.

Tests here verify local deterministic consistency, not provenance, trusted
authorship, mathematical correctness, or regulatory approval.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
import unittest
from unittest.mock import patch

from examples.section_pilot import fixture_problem
from tbdy_column_core.application.services import calculate_section
from tbdy_column_core.domain.quantities import Force,Moment
from tbdy_column_core.domain.section_requests import (
    EnvelopeAtAxialForce,RadialCapacityAtAxialForce,SectionStatus
)
from tbdy_column_core.reporting.section_receipt import (
    RECEIPT_SCHEMA,ReceiptCheckStatus,receipt_for_payload,
    section_report_bundle_json,verify_section_bundle_json
)
from tbdy_column_core.reporting.section_report import (
    section_payload,section_report_json,section_report_html
)


def canonical(d):
    return json.dumps(d,ensure_ascii=False,allow_nan=False,
                      sort_keys=True,separators=(",",":"))


def alter(result,change):
    envelope=json.loads(section_report_bundle_json(result))
    change(envelope)
    return canonical(envelope)


class B6ResultReceiptTests(unittest.TestCase):
    def test_exact_same_result_payload_json_html_and_repeated_bundle(self):
        p=fixture_problem(layout="B")
        result=calculate_section(p)
        bundle=section_report_bundle_json(result)
        data=json.loads(bundle)
        self.assertEqual(data["payload"],json.loads(section_report_json(result)))
        self.assertEqual(data["receipt"]["schema"],RECEIPT_SCHEMA)
        self.assertEqual(data["receipt"]["input_sha256"],
                         result.input_fingerprint.sha256)
        expected=sha256(section_report_json(result).encode("utf-8")).hexdigest()
        self.assertEqual(data["receipt"]["payload_sha256"],expected)
        self.assertIn(expected,section_report_html(result))
        self.assertIn("unsigned",section_report_html(result))
        self.assertEqual(bundle,section_report_bundle_json(result))
        self.assertEqual(verify_section_bundle_json(bundle).status,ReceiptCheckStatus.MATCH)

    def test_input_fingerprint_and_output_hash_distinct_roles(self):
        p=fixture_problem(layout="A")
        normal=calculate_section(p)
        changed=replace(normal,issues=("ADDITIONAL_REPORT_ISSUE",))
        a=json.loads(section_report_bundle_json(normal))
        b=json.loads(section_report_bundle_json(changed))
        self.assertEqual(a["receipt"]["input_sha256"],b["receipt"]["input_sha256"])
        self.assertNotEqual(a["receipt"]["payload_sha256"],b["receipt"]["payload_sha256"])
        self.assertEqual(verify_section_bundle_json(section_report_bundle_json(changed)).status,
                         ReceiptCheckStatus.MATCH)

    def test_changed_actual_force_cannot_retain_old_digest(self):
        r=calculate_section(fixture_problem(layout="B"))
        compromised=alter(r,lambda b:b["payload"]["states"][0].__setitem__(
            "n_n",b["payload"]["states"][0]["n_n"]+1000))
        check=verify_section_bundle_json(compromised)
        self.assertEqual(check.status,ReceiptCheckStatus.MISMATCH)
        self.assertIn("RESULT_PAYLOAD_SHA256_MISMATCH",check.issues)

    def test_changed_issues_status_coverage_and_policy_each_break_receipt(self):
        p=fixture_problem(layout="B",angle_count=8,
                          request=EnvelopeAtAxialForce(Force.kn(500)))
        r=calculate_section(p)
        self.assertEqual(r.status,SectionStatus.COMPLETE_ENVELOPE)
        modifications=(
            lambda b:b["payload"]["issues"].append("ROOT_UNRESOLVED"),
            lambda b:b["payload"].__setitem__("status","PARTIAL_ENVELOPE"),
            lambda b:b["payload"]["angular_coverage"]["missing_indices"].append(3),
            lambda b:b["payload"]["applied_policy"].__setitem__("max_iterations",1),
            lambda b:b["payload"]["states"][0].__setitem__("axial_residual_n",55),
        )
        for i,change in enumerate(modifications):
            with self.subTest(field=i):
                check=verify_section_bundle_json(alter(r,change))
                self.assertEqual(check.status,ReceiptCheckStatus.MISMATCH)
                self.assertIn("RESULT_PAYLOAD_SHA256_MISMATCH",check.issues)

    def test_modified_input_link_rejected_even_if_only_receipt_field_changes(self):
        r=calculate_section(fixture_problem())
        def edit(b):
            b["receipt"]["input_sha256"]="f"*64
        check=verify_section_bundle_json(alter(r,edit))
        self.assertEqual(check.status,ReceiptCheckStatus.MISMATCH)
        self.assertEqual(check.issues,("INPUT_LINK_SHA256_MISMATCH",))

    def test_unknown_versions_duplicate_keys_nonfinite_and_invalid_shape_fail_closed(self):
        r=calculate_section(fixture_problem())
        raw=section_report_bundle_json(r)
        cases=(
            ("no json",ReceiptCheckStatus.MALFORMED),
            ('{"payload":{},"payload":{},"receipt":{}}',ReceiptCheckStatus.MALFORMED),
            (raw.replace('"schema":"column.section.result-receipt.sha256.v1"',
                         '"schema":"unknown.receipt"',1),ReceiptCheckStatus.UNSUPPORTED),
            (raw.replace('"schema":"column.section.numeric.v1.3-b1"',
                         '"schema":"unknown.payload"',1),ReceiptCheckStatus.UNSUPPORTED),
            (raw.replace('"payload_sha256":"','"payload_sha256":"z',1),
             ReceiptCheckStatus.MALFORMED),
            ('{"payload":{"n":NaN},"receipt":{}}',ReceiptCheckStatus.MALFORMED),
            ('{"payload":{},"receipt":{},"extra":1}',ReceiptCheckStatus.MALFORMED),
            ("[]",ReceiptCheckStatus.MALFORMED),
        )
        for text,status in cases:
            with self.subTest(sample=text[:40]):
                check=verify_section_bundle_json(text)
                self.assertEqual(check.status,status,check.issues)

    def test_missing_partial_and_undefined_results_have_distinct_receipts(self):
        p=fixture_problem(layout="B",angle_count=8,max_iterations=1,
                          request=EnvelopeAtAxialForce(Force.kn(500)))
        incomplete=calculate_section(p)
        radial=replace(p,request=RadialCapacityAtAxialForce(
            Force.kn(500),Moment.nmm(0),Moment.nmm(0)))
        undefined=calculate_section(radial)
        a=json.loads(section_report_bundle_json(incomplete))
        b=json.loads(section_report_bundle_json(undefined))
        self.assertNotEqual(a["receipt"]["input_sha256"],b["receipt"]["input_sha256"])
        self.assertNotEqual(a["receipt"]["payload_sha256"],b["receipt"]["payload_sha256"])
        for entry in (a,b):
            self.assertEqual(verify_section_bundle_json(canonical(entry)).status,
                             ReceiptCheckStatus.MATCH)
            self.assertFalse(entry["payload"]["full_column_design_pass"])

    def test_report_receipts_do_not_call_section_solver_or_source_input_digest(self):
        r=calculate_section(fixture_problem())
        with patch("tbdy_column_core.engineering.section_solver.SectionSolver.calculate",
                   side_effect=AssertionError("MUST NOT RUN NUMERIC SOLVER")):
            with patch("tbdy_column_core.engineering.input_identity.section_input_fingerprint",
                       side_effect=AssertionError("MUST NOT REHASH SOURCE")):
                raw=section_report_bundle_json(r)
                html=section_report_html(r)
                self.assertIn(json.loads(raw)["receipt"]["payload_sha256"],html)
                self.assertEqual(verify_section_bundle_json(raw).status,
                                 ReceiptCheckStatus.MATCH)

    def test_unsigned_digest_is_not_an_authentication_signature(self):
        r=calculate_section(fixture_problem())
        bundle=json.loads(section_report_bundle_json(r))
        # An attacker may alter BOTH payload and receipt. It will still
        # match without a trusted external anchor: explicitly demonstrate.
        bundle["payload"]["states"][0]["n_n"]+=1234
        bundle["receipt"]=receipt_for_payload(bundle["payload"])
        self.assertEqual(verify_section_bundle_json(canonical(bundle)).status,
                         ReceiptCheckStatus.MATCH)
        self.assertIn("unsigned",bundle["receipt"]["meaning"])
        self.assertNotIn("approval",bundle["payload"]["status"].lower())


if __name__ == "__main__":
    unittest.main()
