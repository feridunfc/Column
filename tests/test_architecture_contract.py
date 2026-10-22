"""Regression checks for missing/changed governance documents and startup rules."""

from pathlib import Path
import runpy
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CHECKER = runpy.run_path(str(ROOT / "tools/check_architecture_contract.py"))
check_contract = CHECKER["check_contract"]
DOCUMENTS = tuple(CHECKER["EXPECTED_DIGESTS"])


class ArchitectureContractTests(unittest.TestCase):
    def snapshot(self, destination: Path) -> None:
        for relative in (*DOCUMENTS, "AGENTS.md"):
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)

    def test_checked_out_contract_matches_pinned_release(self) -> None:
        self.assertEqual(check_contract(ROOT), ())

    def test_editing_any_canonical_document_blocks_acceptance(self) -> None:
        for relative in DOCUMENTS:
            with self.subTest(document=relative), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                self.snapshot(root)
                path = root / relative
                path.write_bytes(path.read_bytes() + b"\nUnversioned edit\n")
                errors = check_contract(root)
                self.assertTrue(any(relative in error and "SHA-256 mismatch" in error for error in errors))

    def test_missing_constitution_blocks_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.snapshot(root)
            (root / DOCUMENTS[0]).unlink()
            self.assertTrue(any("unavailable" in error for error in check_contract(root)))

    def test_removing_read_first_entry_point_blocks_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.snapshot(root)
            path = root / "AGENTS.md"
            path.write_text(path.read_text(encoding="utf-8").replace("## READ_BEFORE_WORK", "## Removed"), encoding="utf-8")
            self.assertTrue(any("read-before-work" in error for error in check_contract(root)))


if __name__ == "__main__":
    unittest.main()
