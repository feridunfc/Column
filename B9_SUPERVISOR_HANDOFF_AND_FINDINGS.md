# B9 — Supervisor handoff / unresolved engineering disposition

**Date:** 2026-10-23
**B8 base code+ledger HEAD:** `2e18d53fdbab08fc9c058712af579e95d93f7b1e`
**Review preparer:** Worker, not an independent acceptance owner.
**Disposition:** `HOLD / NOT_INDEPENDENTLY_ACCEPTED`

## Fixed anchor / work done

The B1–B8 chain is frozen as consecutive draft PRs; no main merge.
The current source tree has been inspected for numerical and API scope.
Read-only G0/G1/G2 review targets are the full v1.3.1 constitution
and all acceptance-test records tied to exact B9 HEAD and tree.
CI and local test completion do not substitute the Supervisor's
independent assessment.

## Source-driven blocking findings

| ID | Criticality | Source and observation | Required closure |
|---|---|---|---|
| B9-F01 | BLOCKER | C-01/C-02/C-32 require complete independent G0/G1/G2 reading, approval sequence and formal ratification. The batch-sprint process deviation is recorded but not ratified in a new constitutional version. | An authorized independent Supervisor records G0/G1/G2 decisions against exact HEAD/tree, with C-02 explicit disposition by owner before any ACCEPTED_AB. |
| B9-F02 | BLOCKER | C-20, C-29, AB-12: source single-angle root solver samples only and can return its first crossing. B6 adds a 359-point matching bracket check, **but globally unique roots cannot be proved** and tangent roots narrower than sampling can be missed. | Independent engineering basis or conservative bounded root procedure for the allowed domain. Give real counterexamples, criteria and explicit unresolved states; never claim uniqueness on sampled evidence alone. |
| B9-F03 | BLOCKER | C-20/AB-12: radial hull from finite sampled angles. The B2 8→16 sample has delta 200325.843677 Nmm against 1000 Nmm moment budget; B7 tests 72/144/288 and independent oracle at 3% as broad regression, **not** a certified 1000 Nmm angular error bound. | Review 72/144/288 measured deltas separately from independent oracle agreement, establish a justified acceptance budget and fail-closed policy; do not silently widen tolerance to pass. |
| B9-F04 | REVIEW HOLD | C-13/C-14: typed `SourceMetadata`, `EvidenceCatalog` and `AnalysisBundle.qualify` enforce provenance/role/consumer/coverage contracts, but authenticity of a real external verifier/record cannot be established by constructing typed receipts. | Independent review of source scope and negative role/producer/semantics tests with a concrete authenticated producer integration when required. |
| B9-F05 | REVIEW HOLD | C-28 and A/B reports: numerical result is explicitly **not** a column design check. Partial envelope, missing member demand, stability, shear, confinement, joint checks remain unperformed. | No claim beyond A/B. A/B can be accepted only to its constitutional scope, after full G0/G1/G2 review. |

## Observed angular-resolution numerical failure — measured B9 CI

**Evidence:** exact code HEAD `b9bc32f8500354ff8bc669f9021869484aa7390c`,
run `39911340948`, all four environments successful at the
development/test level, producing matching numeric observations:

| Angle population | Sampled radial capacity (Nmm) | kNm |
|---|---:|---:|
| 72 | 264894954.85597295 | 264.894954856 |
| 144 | 264910256.12575525 | 264.910256126 |
| 288 | 264917904.34415603 | 264.917904344 |

- 72→144 observed difference = **15301.2697823 Nmm**.
- 144→288 observed difference = **7648.2184008 Nmm**.
- User-supplied numerical policy Moment budget = **1000 Nmm**
  for *each* step, relative tolerance = 0.
- Both differences exceed budget. B9 numeric verdict:
  `OBSERVED_NOT_STABLE`. The ratio to allowed budget is about
  15.30 and 7.65, respectively.
- The two sampled differences diminish but do **not** prove the limit
  has converged, nor do they identify an acceptable final angular
  resolution or globally unique axial root.

**FND-B9-03 remains BLOCKER** on those concrete measurements. The
source-bound physics, numerical-policy value and independent oracle
were **not** adjusted to make this pass. The clear next engineering
task is a methodologically justified angular refinement/capacity
extraction strategy and explicit policy/fail-closed status, reviewed
independently before any release.

## Procedural review steps for independent acceptance owner

1. Independently read `COLUMN_CONSTITUTION.md`, `COLUMN_WORKER_AB.md`,
   `COLUMN_SUPERVISOR.md`, `AGENTS.md` and all B1–B9 sprint
   changes, not summaries alone. Independently compute SHA256 and verify
   pinned kernel, test-only oracle and legacy source.
2. Confirm branch ancestry, protected main, HEAD/TREE cleanliness,
   source imports, B8 ledger 32 C + 18 AB entries.
3. Re-run strict contract check, all tests and offline examples
   on exact HEAD; independently check 72/144/288 angular and source
   root anomalies plus two cages at three strain states.
4. Give explicit findings for each mandatory C clause and AB check:
   `SATISFIED`, `UNVERIFIED`, `VIOLATION`, or legitimately
   `PRESERVED_DEFERRED`. Cite symbol/test, exact numerical
   comparison and remediation criterion.
5. Record independent G0, then G1, then G2 acceptance only if all
   earlier blockers are actually resolved. A code commit after review
   invalidates affected tests/reviews; rerun them.
6. Make the owner's formal C-02 disposition visible. An unratified
   process deviation cannot be silently waved through by green CI.

## Verification reproduction — local tests deferred by user

```powershell
python tools/check_architecture_contract.py
python tools/validate_b8_ledger.py
python -m tools.b9_review_release_gate
python -B -m unittest discover -s tests -v
python -B -m examples.section_pilot
python -B -m examples.b9_numerical_review
```

The executable B9 gate only verifies a **HOLD**, never fabricates a
Supervisor signature, approval, or TS500/TBDY code assessment.

## Recorded disposition

`G0=NOT_ACCEPTED`
`G1=NOT_ACCEPTED`
`G2=NOT_ACCEPTED`
`ACCEPTED_AB=NO`
`B9_REVIEW_HANDOFF=PREPARED`
`RELEASE=HOLD`

These are evidence of incomplete independent review, not adverse
design findings on any real column. The user may perform local tests
after all sprint commits; pass/fail will refine the evidence but
cannot itself close C-02/G0/G1/G2.
