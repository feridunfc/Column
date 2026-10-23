"""B8: ledger population and negative release-claim protection."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.validate_b8_ledger import LEDGER,validate_ledger


class B8LedgerTests(unittest.TestCase):
    def test_full_rows_and_hold(self):
        x=validate_ledger()
        self.assertEqual(len(x["constitution_rows"]),32)
        self.assertEqual(len(x["acceptance_rows"]),18)
        self.assertEqual(x["release_gate"],"HOLD")
        self.assertEqual(x["c02_process_status"],"OPEN_UNRATIFIED")
        self.assertFalse(x["claims"]["angular_error_bound_certified"])

    def test_mutated_missing_and_forged_approval_fail(self):
        original=validate_ledger()
        for method in ("drop","approve","no_file","bad_status"):
            doc=json.loads(json.dumps(original))
            if method=="drop":
                doc["constitution_rows"].pop()
            elif method=="approve":
                doc["release_gate"]="ACCEPTED_AB"
            elif method=="no_file":
                doc["acceptance_rows"][0]["evidence_paths"]=["unknown/file"]
            else:
                doc["constitution_rows"][5]["worker_assessment"]="UNKNOWN"
            with self.subTest(method=method),TemporaryDirectory() as temp:
                p=Path(temp)/"broken.json"
                p.write_text(json.dumps(doc),encoding="utf-8")
                with self.assertRaises(ValueError):
                    validate_ledger(p)


if __name__=="__main__":
    unittest.main()
