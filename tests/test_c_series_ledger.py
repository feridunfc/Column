"""C-series ledger integrity: no sprint can become self-approved by prose.

Structural process test only; it does NOT replace engineering/Supervisor gates.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"docs"/"c_series"/"SPRINT_LEDGER.json"
SHA=re.compile(r"^[0-9a-f]{40}$")
STATES={"PLANNED","TESTED_DRAFT","BLOCKED","FIXED_PENDING_REVIEW","ACCEPTED"}


class CSeriesLedgerTests(unittest.TestCase):
    def load(self):
        return json.loads(LEDGER.read_text(encoding="utf-8"))

    def test_every_sprint_present_once_and_ordered(self):
        src=self.load()
        self.assertEqual(src["constitution_release"],"COLUMN-OOP-1.3.1-20261022")
        self.assertEqual([r["id"] for r in src["sprints"]],[f"C{i}" for i in range(9)])
        self.assertEqual(len({x["scope_key"] for x in src["sprints"]}),9)
        self.assertEqual(src["product_release"],"HOLD")
        self.assertTrue(src["change_control"]["canonical_docs_unchanged"])

    def test_tested_code_must_have_commit_and_evidence(self):
        src=self.load()
        for sprint in src["sprints"]:
            with self.subTest(sprint=sprint["id"]):
                self.assertIn(sprint["status"],STATES)
                self.assertTrue(sprint["constitution_clauses"])
                self.assertTrue(sprint["required_negative_evidence"])
                if sprint["status"] in {"TESTED_DRAFT","FIXED_PENDING_REVIEW","ACCEPTED"}:
                    self.assertRegex(sprint["origin_head"],SHA)
                    self.assertRegex(sprint["integrated_candidate_head"],SHA)
                    self.assertTrue(sprint["files"])
                    self.assertTrue(sprint["evidence"])
                if sprint["status"]=="ACCEPTED":
                    self.assertNotEqual(sprint["supervisor_disposition"],"PENDING")
                    self.assertNotEqual(src["change_control"]["state"],"PROPOSED_NOT_RATIFIED")

    def test_numerical_blockers_and_scope_change_cannot_disappear(self):
        src=self.load()
        findings={v["id"]:v for v in src["open_findings"]}
        self.assertTrue({"B9-F02","B9-F03","C02-SCOPE"}.issubset(findings))
        self.assertEqual(findings["B9-F02"]["status"],"OPEN")
        self.assertEqual(findings["B9-F03"]["status"],"OPEN")
        for sprint in src["sprints"]:
            self.assertNotEqual(sprint["supervisor_disposition"],"ACCEPTED" if
                                sprint["status"]!="ACCEPTED" else "PENDING")
