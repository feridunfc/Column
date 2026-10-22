"""A0: tamper-resistant canonical document/entry verification."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.check_architecture_contract import (
    ArchitectureContractError, DOCS, validate,
)

ROOT = Path(__file__).resolve().parents[1]


class ArchitectureContractTests(unittest.TestCase):
    def test_complete_repo_contract(self):
        self.assertEqual(len(validate(ROOT)), 3)

    def _copy(self, temp):
        target = Path(temp)
        for name in (*DOCS, "AGENTS.md"):
            (target / name).write_bytes((ROOT / name).read_bytes())
        return target

    def test_changed_constitution_fails_without_relocking(self):
        with TemporaryDirectory() as temp:
            folder = self._copy(temp)
            file = folder / DOCS[0]
            file.write_bytes(file.read_bytes() + b"\n")
            with self.assertRaises(ArchitectureContractError):
                validate(folder)

    def test_missing_document_fails(self):
        with TemporaryDirectory() as temp:
            folder = self._copy(temp)
            (folder / DOCS[1]).unlink()
            with self.assertRaises(ArchitectureContractError):
                validate(folder)

    def test_missing_full_read_agent_fails(self):
        with TemporaryDirectory() as temp:
            folder = self._copy(temp)
            (folder / "AGENTS.md").write_text("hello", encoding="utf-8")
            with self.assertRaises(ArchitectureContractError):
                validate(folder)

    def test_crlf_checkout_accepted_bom_rejected(self):
        with TemporaryDirectory() as temp:
            folder = self._copy(temp)
            name = folder / DOCS[0]
            name.write_bytes(name.read_bytes().replace(b"\n", b"\r\n"))
            self.assertEqual(len(validate(folder)), 3)
            name.write_bytes(b"\xef\xbb\xbf" + name.read_bytes())
            with self.assertRaises(ArchitectureContractError):
                validate(folder)


if __name__ == "__main__":
    unittest.main()
