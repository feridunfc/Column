"""B9 regression enforces no self-certified independent Supervisor."""
import unittest
from tools.b9_review_release_gate import ReviewGate,evaluate_b9_readiness


class B9GateTests(unittest.TestCase):
    def test_worker_handoff_cannot_be_release_acceptance(self):
        outcome=evaluate_b9_readiness()
        self.assertEqual(outcome.gate,ReviewGate.HOLD)
        self.assertFalse(outcome.supervisor_independent)
        self.assertIn("C02_VERSIONED_PROCESS_CHANGE_NOT_RATIFIED",outcome.open_reasons)
        self.assertIn("INDEPENDENT_SUPERVISOR_GATE_NOT_COMPLETED",outcome.open_reasons)
        self.assertIn("OPEN_FINDING_FND-B8-02",outcome.open_reasons)
        self.assertGreaterEqual(len(outcome.open_reasons),5)

if __name__=="__main__":
    unittest.main()
