"""B6 output receipts: byte integrity, result identity and explicit limitations."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
import unittest
from unittest.mock import patch

from examples.section_pilot import fixture_problem
from tbdy_column_core.application.services import calculate_section
from tbdy_column_core.domain.quantities import Angle, Force, Length, Moment
from tbdy_column_core.domain.section_requests import (
    AtStrainState,EnvelopeAtAxialForce,RadialCapacityAtAxialForce,SectionStatus,
)
from tbdy_column_core.reporting.section_report import section_report_json,section_report_html
from tbdy_column_core.reporting.receipt import (
    RECEIPT_SCHEMA, SectionOutputReceipt, seal_section_report,
    section_output_receipt_json, verify_sealed_section_report,
)


class B6SectionReceiptTests(unittest.TestCase):
    def test_repeated_result_has_stable_byte_hashes_and_input_link(self):
        problem=fixture_problem(layout="B")
        result=calculate_section(problem)
        a=seal_section_report(result)
        b=seal_section_report(calculate_section(problem))
        self.assertEqual(a,b)
        self.assertEqual(a.result_json,section_report_json(result))
        self.assertEqual(a.report_html,section_report_html(result))
        self.assertEqual(a.receipt.schema,RECEIPT_SCHEMA)
        self.assertEqual(a.receipt.input_sha256,result.input_fingerprint.sha256)
        self.assertEqual(a.receipt.result_json_sha256,
                         sha256(a.result_json.encode("utf-8")).hexdigest())
        self.assertEqual(a.receipt.report_html_sha256,
                         sha256(a.report_html.encode("utf-8")).hexdigest())
        self.assertTrue(verify_sealed_section_report(a).bytes_match)
        self.assertEqual(json.loads(section_output_receipt_json(a.receipt))["input_sha256"],
                         result.input_fingerprint.sha256)

    def test_same_input_fingerprint_different_output_is_not_same_result(self):
        problem=fixture_problem()
        result=calculate_section(problem)
        altered_state=replace(result.states[0],
                              n=Force.n(result.states[0].n.as_n + 10.))
        modified=replace(result,states=(altered_state,))
        self.assertEqual(result.input_fingerprint,modified.input_fingerprint)
        orig=seal_section_report(result)
        updated=seal_section_report(modified)
        self.assertNotEqual(orig.receipt.result_json_sha256,
                            updated.receipt.result_json_sha256)
        self.assertNotEqual(orig.receipt.report_html_sha256,
                            updated.receipt.report_html_sha256)
        self.assertTrue(verify_sealed_section_report(updated).bytes_match)
        # Byte matching does not imply the modified numerical value is true.

    def test_tampered_json_html_and_receipt_are_detected_independently(self):
        bundle=seal_section_report(calculate_section(fixture_problem()))
        edited=replace(bundle,result_json=bundle.result_json.replace(
            '"status":"NUMERIC_STATE"', '"status":"NUMERIC_UNRESOLVED"'))
        check=verify_sealed_section_report(edited)
        self.assertFalse(check.bytes_match)
        self.assertIn("RESULT_JSON_BYTES_CHANGED",check.issues)
        self.assertIn("RESULT_STATUS_MISMATCH",check.issues)
        changed_html=replace(bundle,report_html=bundle.report_html+"<!-- altered -->")
        check=verify_sealed_section_report(changed_html)
        self.assertFalse(check.bytes_match)
        self.assertIn("REPORT_HTML_BYTES_CHANGED",check.issues)
        new_receipt=replace(bundle.receipt,input_sha256="0"*64)
        check=verify_sealed_section_report(replace(bundle,receipt=new_receipt))
        self.assertFalse(check.bytes_match)
        self.assertIn("DECLARED_INPUT_DIGEST_MISMATCH",check.issues)

    def test_unchanged_semantic_json_with_different_bytes_is_not_same_snapshot(self):
        bundle=seal_section_report(calculate_section(fixture_problem()))
        pretty=json.dumps(json.loads(bundle.result_json),indent=2,ensure_ascii=False)
        self.assertEqual(json.loads(pretty),json.loads(bundle.result_json))
        rebased=replace(bundle,result_json=pretty)
        self.assertIn("NONCANONICAL_RESULT_JSON",
                      verify_sealed_section_report(rebased).issues)
        # Even if the digest is recomputed by the caller, canonical-byte
        # mismatch stays explicit and this is not a cryptographic signature.
        forged_receipt=replace(bundle.receipt,
            result_json_sha256=sha256(pretty.encode("utf-8")).hexdigest())
        self.assertIn("NONCANONICAL_RESULT_JSON",
                      verify_sealed_section_report(replace(rebased,receipt=forged_receipt)).issues)

    def test_nonfinite_json_rejected_even_with_matching_digest(self):
        bundle=seal_section_report(calculate_section(fixture_problem()))
        tampered=bundle.result_json.replace('"angle_deg":', '"angle_deg":NaN, "extra":')
        receipt=replace(bundle.receipt,
                result_json_sha256=sha256(tampered.encode("utf-8")).hexdigest())
        integrity=verify_sealed_section_report(replace(
            bundle,result_json=tampered,receipt=receipt))
        self.assertFalse(integrity.bytes_match)
        self.assertIn("INVALID_RESULT_JSON",integrity.issues)

    def test_partial_unresolved_and_undefined_are_sealed_without_code_pass(self):
        cases=(
            fixture_problem(layout="B",angle_count=8,max_iterations=1,
                request=EnvelopeAtAxialForce(Force.kn(500))),
            fixture_problem(layout="B",angle_count=8,
                request=RadialCapacityAtAxialForce(
                    Force.kn(500),Moment.nmm(0),Moment.nmm(0))),
            fixture_problem(layout="B",
                request=AtStrainState(Angle.deg(33),Length.mm(240))),
        )
        for p in cases:
            with self.subTest(request=type(p.request).__name__):
                result=calculate_section(p)
                package=seal_section_report(result)
                self.assertTrue(verify_sealed_section_report(package).bytes_match)
                self.assertEqual(package.receipt.result_status,result.status.value)
                self.assertFalse(json.loads(package.result_json)["full_column_design_pass"])
                self.assertIn("not a signature",
                              section_output_receipt_json(package.receipt))

    def test_receipt_is_passive_and_rejects_invalid_typed_payload(self):
        result=calculate_section(fixture_problem())
        from tbdy_column_core.engineering.section_solver import SectionSolver
        with patch.object(SectionSolver,"calculate",
                          side_effect=AssertionError("must not run solver")):
            package=seal_section_report(result)
            integrity=verify_sealed_section_report(package)
        self.assertTrue(integrity.bytes_match)
        with self.assertRaises(TypeError):
            seal_section_report({"status":"fake"})
        with self.assertRaises(TypeError):
            verify_sealed_section_report(result)
        with self.assertRaises(ValueError):
            replace(package.receipt,result_json_sha256="bad")
        with self.assertRaises(ValueError):
            replace(package.receipt,schema="OTHER")


if __name__=="__main__":
    unittest.main()
