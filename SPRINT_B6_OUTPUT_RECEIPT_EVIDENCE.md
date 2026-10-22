# Column B6 — Unsigned output receipt and report-content binding

Date: 2026-10-22
Base: B5 `a8e623beafc9362af991aab9a67e059a14d3d19e`
Worker branch: `worker/v131-b6-output-receipt-20261022`

## Issue and bounded change

B5 pins the *declared calculation inputs* but a calculation's
`status`, `issues`, solved `N/M2/M3`, sampled root diagnostics and
radial capacity can differ even when inputs and source labels are
unchanged. One input hash is therefore not a result identity.

B6 introduces `section_receipt.py` for a deterministic, **unsigned**
SHA-256 checksum of a canonical JSON representation of the complete
read-only `SectionCapacityResult` projection, including the B5 input
fingerprint. The output digest excludes its own receipt to avoid circular
hashing. This is a calculation-report integrity check, not an execution
signature.

- The same passive `section_payload(result)` adds
  `output_receipt = {schema, sha256, input_sha256, meaning}`.
- JSON and HTML use that exact payload, displaying both the input
  binding and the separate output digest. No model, root or strength
  evaluation runs during rendering.
- `verify_section_report_json(report)` checks the envelope schema, B5
  input digest, output checksum and embedded input-digest binding.
  It rejects malformed JSON, duplicate JSON keys, unknown receipt
  schema, NaN, missing/changed receipt and modified result fields.
- The checksum contains the entire reported section identity,
  model/frame, reference/source revisions, requested/applied policy,
  root quality, angular coverage, issue list and numerical states.
  It also includes the declared noncompliance scope.
- Existing numerical result object, engineering kernel, B5 input hash,
  JSON numeric schema version and public `calculate_section` signature
  remain unchanged. The new report key is additive.

## Engineering and security boundary

An untrusted party who can rewrite the report can recompute SHA-256;
`verify_section_report_json` then passes the rewritten content. A
positive verification means **self-consistent unsigned content only**.
It is NOT proof of producer authenticity, immutable hosting, trusted
execution, a source file's genuineness, numerical correctness, or
TS500/TBDY full-column approval. No signing key, remote authority,
external storage or timestamp was added.

## Test plan and acceptance evidence

Eight new isolated tests cover: passive deterministic receipt, input
binding, same input/different output distinction, changed
status/issue/policy/angle-coverage digest, JSON tampering of numbers and
source revisions, invalid/duplicate-key/NaN, absence of production physics
during reporting, unsupported and unresolved outcomes, and a deliberately
resigned forged checksum passing to document the unsigned limit.

```powershell
python tools/check_architecture_contract.py
python -B -m unittest discover -s tests -v
python -B -m examples.section_pilot
```

The architecture's three canonical documents and the physics/oracle
sources were not changed.

User-directed process C-02 continues as OPEN: B1–B6 Worker development
is staged for one later independent Supervisor G0/G1/G2 review. No merge
into main, no `ACCEPTED_AB`, no real building design PASS.
