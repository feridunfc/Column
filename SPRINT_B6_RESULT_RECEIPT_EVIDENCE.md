# Column v1.3.1 — B6 deterministic output receipt (draft)

**Baseline:** B5 `a8e623beafc9362af991aab9a67e059a14d3d19e`
**Worker branch:** `worker/v131-b6-result-receipt-20261022`
**Review:** Independent G0/G1/G2 NOT ACCEPTED and formal C-02 procedural
amendment unresolved. All development remains a draft PR; no main merge.

## Issue and bounded solution

The B5 `CalculationInputFingerprint` binds *declared input* to the
finished `SectionCapacityResult`, including section geometry, supplied
reinforcing bars, steel laws, request, tolerance policy, reference frame,
kernel identifier and declared source revisions. It does **not**
differentiate two possible numerical results produced for the same
inputs, and it does not bind any exported report bytes.

B6 introduces `SealedSectionReport` with:
- Exact existing `section_report_json(result)` and
  `section_report_html(result)` UTF-8 report snapshots;
- `SectionOutputReceipt` containing `input_sha256`,
  `result_json_sha256`, `report_html_sha256`, exact numerical result
  status, report schema and kernel identifier;
- A deterministic strict JSON serialization of the *receipt*;
- A passive, offline `verify_sealed_section_report(bundle)` returning
  `ReportIntegrityCheck(bytes_match, issues)`.

Receipt verification checks SHA-256 of both saved byte streams and
the declared input digest/status/schema/kernel visible inside saved
canonical JSON. Strict canonical sorted UTF-8 JSON is required; invalid
JSON, nonfinite numeric constants, mutated bytes and cross-document
identity mismatches yield typed, explicit issues. Neither step
calls the section physics engine or external source adapters.

## Integrity versus authority (critical)

An integrity status `bytes_match=True` means only that the available
receipt and snapshot bytes agree. An attacker controlling both content
and receipt can recompute matching SHA-256 digests. **No digital
signature, authentication, independent calculation oracle, source
authenticity or normative TS500/TBDY approval is provided.**

One immutable input digest may accompany different numeric output
digests. A changed status, force/moment, residual, coverage, issue,
source trace or report rendering is therefore no longer silently
identified only by the same input digest. JSON and HTML have
independent artifact digests, making a presentation-only change
separate from a calculation-data change.

The term `SealedSectionReport` refers to a passive immutable in-memory
snapshot; this module does not persist it, use an authoritative clock,
create a server-side trust anchor or audit who produced its bytes.
A later signed-artifact or external evidence layer, if required,
must be separately designed and reviewed.

## Regression evidence

Seven new tests check:
1. Same input/result reproducible SHA-256 and receipt/report linkage.
2. Same input SHA-256, changed numeric state -> changed output digest.
3. Independent JSON, HTML, and declared input-link tamper detection.
4. Reformatting with equivalent parsed JSON -> byte-level mismatch.
5. Nonfinite JSON rejection even when an altered hash matches.
6. Unresolved/undefined/direct numeric statuses retained without
   invented `full_column_design_pass`.
7. No calculation on seal or verification; invalid types/digest
   contracts rejected.

CI for code commit `10684a941cc0acf2bbb45cf35e9eed5d2cbd5054`:
https://github.com/feridunfc/Column/actions/runs/39834408643

**62/62 tests OK** on Ubuntu Python 3.12/3.13 and Windows
Python 3.12/3.13. Original three document hashes checked;
existing offline pilot also ran successfully. The final example-only
commit is subject to its own CI.

## Exact local commands (when user elects to run tests)

```powershell
python tools/check_architecture_contract.py
python -B -m unittest discover -s tests -v
python -B -m examples.section_pilot
```

The user's local tests and batched independent Supervisor review remain
deferred by request; do not label this `G1_ACCEPTED`, `G2_ACCEPTED` or
`ACCEPTED_AB`. Original source TS500 kernel and independent oracle
are unchanged. No ETABS, global response compiler, member analysis,
second-order, shear, confinement, candidate generator or model mutation.
