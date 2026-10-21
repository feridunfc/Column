"""S1-H acceptance contract: real source ZIP required for live-source gates.

CI uses pure negative/shape tests; the real archive tests execute only when
COLUMN_S1H_SOURCE_ZIP is set to an operator-supplied original archive.
No fake 'READY', fabricated EDB, COM or native operations in these tests.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from io import BytesIO
from json import loads
import ast
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import warnings
from zipfile import ZipFile

from tbdy_column_core.s1g_archive import KNOWN_RECORDED_SHA, KNOWN_CUTSET_SHA, KNOWN_STABILITY_SHA
from tbdy_column_core.s1h_recovery import (
    PINNED, REC, CUT, STAB, SOURCE_PRODUCERS, S1HError, Lane,
    derive_recovery_plan, plan_from_archive_zip,
)

ENV = "COLUMN_S1H_SOURCE_ZIP"
ZIP = os.environ.get(ENV, "")
EXPECTED = tuple(f"H{i:02}" for i in range(1, 13))
CAPTURE = ("H04", "H05", "H07", "H08", "H11")


def _zip_fixture(members: tuple[tuple[str, bytes], ...]) -> BytesIO:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, content in members:
            archive.writestr(name, content)
    buffer.seek(0)
    return buffer


def _archive_bytes():
    with ZipFile(ZIP) as archive:
        return {name: archive.read(name) for name in PINNED}


class S1HBoundariesWithoutExternalArchive(unittest.TestCase):
    def test_nine_original_sources_are_sha256_pinned(self):
        self.assertEqual(len(PINNED), 9)
        self.assertEqual(PINNED[REC], KNOWN_RECORDED_SHA)
        self.assertEqual(PINNED[CUT], KNOWN_CUTSET_SHA)
        self.assertEqual(PINNED[STAB], KNOWN_STABILITY_SHA)
        self.assertEqual(len(set(PINNED)), 9)
        for digest in PINNED.values():
            self.assertEqual(len(digest), 64)
            self.assertEqual(digest, digest.lower())
            self.assertEqual(set(digest) - set("0123456789abcdef"), set())

    def test_no_arbitrary_source_document_becomes_authority(self):
        fake = {name: b'{"READY":true,"status":"APPROVED"}'
                for name in PINNED}
        with self.assertRaisesRegex(S1HError, "PINNED_SOURCE_CHANGED"):
            derive_recovery_plan(fake)

    def test_missing_pinned_source_is_rejected_not_defaulted(self):
        with self.assertRaisesRegex(S1HError, "MISSING_PINNED_SOURCE"):
            derive_recovery_plan({})

    def test_real_source_reference_cannot_be_replaced_by_same_named_json(self):
        fake = {name: b"{}" for name in PINNED}
        self.assertNotEqual(sha256(fake[REC]).hexdigest(), PINNED[REC])
        with self.assertRaisesRegex(S1HError, "PINNED_SOURCE_CHANGED"):
            derive_recovery_plan(fake)

    def test_empty_zip_has_explicit_missing_original_source_error(self):
        with TemporaryDirectory() as folder:
            p = Path(folder) / "empty.zip"
            with ZipFile(p, "w"):
                pass
            with self.assertRaisesRegex(S1HError, "MISSING_PINNED_SOURCE"):
                plan_from_archive_zip(p)

    def test_duplicate_zip_member_fails_before_extract(self):
        name = next(iter(PINNED))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            archive = _zip_fixture(((name, b"first"), (name, b"second")))
        with TemporaryDirectory() as folder:
            p = Path(folder) / "duplicate.zip"
            p.write_bytes(archive.getvalue())
            with self.assertRaisesRegex(S1HError, "DUPLICATE_ZIP_MEMBER_NAMES"):
                plan_from_archive_zip(p)

    def test_oversized_original_document_is_rejected_before_read(self):
        name = next(iter(PINNED))
        archive = _zip_fixture(((name, b"x" * 250_001),))
        with TemporaryDirectory() as folder:
            p = Path(folder) / "oversize.zip"
            p.write_bytes(archive.getvalue())
            with self.assertRaisesRegex(S1HError, "PINNED_SOURCE_SIZE_LIMIT"):
                plan_from_archive_zip(p)

    def test_unrelated_member_does_not_satisfy_missing_pinned_source(self):
        archive = _zip_fixture((("source/docs/fake_source.json", b'{"READY":true}'),))
        with TemporaryDirectory() as folder:
            p = Path(folder) / "unrelated.zip"
            p.write_bytes(archive.getvalue())
            with self.assertRaisesRegex(S1HError, "MISSING_PINNED_SOURCE"):
                plan_from_archive_zip(p)

    def test_all_discovery_paths_are_code_inventory_not_runtime_proof(self):
        self.assertEqual(len(SOURCE_PRODUCERS), 5)
        self.assertTrue(all(path.startswith("source/") for path in SOURCE_PRODUCERS))
        self.assertTrue(all(path.endswith(".py") for path in SOURCE_PRODUCERS))

    def test_s1h_source_has_no_native_etabs_transport_import(self):
        source = Path(__file__).resolve().parents[1] / "tbdy_column_core" / "s1h_recovery.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module or "")
        self.assertFalse(any(
            "win32com" in s or "comtypes" in s or "etabs_gateway" in s or
            "pythoncom" in s
            for s in imports))
        self.assertNotIn("subprocess", imports)
        self.assertNotIn("requests", imports)


@unittest.skipUnless(ZIP, "Set COLUMN_S1H_SOURCE_ZIP to run original-archive gates")
class S1HRealOriginalArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = Path(ZIP)
        if not cls.p.is_file():
            raise AssertionError(f"Missing exact original archive: {cls.p}")
        cls.original_bytes = cls.p.read_bytes()
        cls.before = sha256(cls.original_bytes).hexdigest()
        cls.blobs = _archive_bytes()

    def test_actual_nine_source_bytes_have_exact_pins(self):
        self.assertEqual(set(self.blobs), set(PINNED))
        self.assertEqual(
            {p: sha256(data).hexdigest() for p, data in self.blobs.items()},
            PINNED,
        )

    def test_original_plan_matches_twelve_unique_recovery_ids(self):
        plan = derive_recovery_plan(self.blobs)
        self.assertEqual(plan.schema, "column.s1h.offline-source-routing.v1")
        self.assertEqual(tuple(item.id for item in plan.items), EXPECTED)
        self.assertEqual(plan.archive_document_count, 9)
        self.assertEqual(plan.preserved_native_fact_count, 5)
        self.assertEqual(plan.original_235_frameforce_rows, 60)
        self.assertEqual(plan.future_capture_order, CAPTURE)

    def test_two_independent_invocations_are_bitwise_deterministic(self):
        a, b = plan_from_archive_zip(self.p), plan_from_archive_zip(self.p)
        self.assertEqual(a.json(), b.json())

    def test_s1h_never_promotes_legacy_force_or_current_design(self):
        plan = plan_from_archive_zip(self.p)
        self.assertEqual(plan.status, "SOURCE_RECOVERY_PLAN_PREPARED_CURRENT_DESIGN_BLOCKED")
        self.assertEqual(plan.component_id, "235")
        self.assertFalse(plan.source_models_rebound)
        self.assertFalse(plan.full_project_design_proven)
        self.assertFalse(plan.etabs_live_executed)
        self.assertNotEqual(plan.recorded_model_sha256, plan.candidate_model_sha256)
        self.assertEqual(plan.source_digest_sha256, PINNED)

    def test_routes_preserve_offline_before_future_gateway(self):
        plan = plan_from_archive_zip(self.p)
        by_id = {r.id: r for r in plan.items}
        self.assertEqual(by_id["H03"].lane, Lane.OFFLINE_PROJECT_DOCUMENT_REVIEW)
        self.assertEqual(by_id["H04"].lane, Lane.OFFLINE_FILE_OR_EXPORT_SEARCH)
        self.assertEqual(by_id["H06"].lane, Lane.OFFLINE_FACT_RECONCILIATION)
        for key in ("H05", "H07", "H08", "H11"):
            self.assertEqual(by_id[key].lane, Lane.FUTURE_GATEWAY_IF_EXPORT_ABSENT)
            self.assertIn("Search", by_id[key].next_action)
        self.assertEqual(by_id["H09"].lane, Lane.DERIVE_AFTER_PREREQUISITES)
        self.assertEqual(by_id["H10"].lane, Lane.DERIVE_AFTER_PREREQUISITES)
        self.assertEqual(by_id["H12"].lane, Lane.DERIVE_AFTER_PREREQUISITES)

    def test_prerequisites_reference_valid_items_and_are_acyclic(self):
        plan = plan_from_archive_zip(self.p)
        ids = set(EXPECTED)
        edges = {r.id: r.prerequisites for r in plan.items}
        for name, deps in edges.items():
            self.assertNotIn(name, deps)
            self.assertTrue(set(deps) <= ids)
        explored, stack = set(), set()
        def check(node):
            if node in stack:
                self.fail("cyclic engineering prerequisite")
            if node in explored:
                return
            stack.add(node)
            for dep in edges[node]:
                check(dep)
            stack.remove(node)
            explored.add(node)
        for node in ids:
            check(node)

    def test_each_of_nine_one_byte_source_mutations_fails_closed(self):
        for name, content in self.blobs.items():
            with self.subTest(path=name):
                damaged = dict(self.blobs)
                damaged[name] = content + b" "
                with self.assertRaisesRegex(S1HError, "PINNED_SOURCE_CHANGED"):
                    derive_recovery_plan(damaged)

    def test_each_of_nine_missing_pinned_documents_fails_closed(self):
        for name in self.blobs:
            with self.subTest(path=name):
                damaged = dict(self.blobs)
                del damaged[name]
                with self.assertRaisesRegex(S1HError, "MISSING_PINNED_SOURCE"):
                    derive_recovery_plan(damaged)

    def test_real_zip_is_unchanged_by_recovery_plan(self):
        original_sha = sha256(self.p.read_bytes()).hexdigest()
        plan = plan_from_archive_zip(self.p)
        self.assertFalse(plan.etabs_live_executed)
        self.assertEqual(sha256(self.p.read_bytes()).hexdigest(), original_sha)
        self.assertEqual(original_sha, self.before)

    def test_plan_output_is_parseable_json_without_nonfinite_numbers(self):
        plan = plan_from_archive_zip(self.p)
        payload = loads(plan.json(), parse_constant=lambda _: self.fail("non-finite JSON"))
        self.assertEqual(len(payload["items"]), 12)
        self.assertFalse(payload["full_project_design_proven"])
        self.assertEqual(payload["future_capture_order"], list(CAPTURE))


if __name__ == "__main__":
    unittest.main()
