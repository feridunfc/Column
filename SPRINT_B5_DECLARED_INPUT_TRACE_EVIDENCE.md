# Column v1.3.1 — Sprint B5 / Declared section input trace

**Date:** 2026-10-22
**Repository:** `feridunfc/Column`
**Base:** B4 HEAD `3e1f750a82de911e5973b27c1f011fc47310d3ff`
**Worker branch:** `worker/v131-b5-input-trace-20261022`

## Purpose / contract

The B1–B4 section reports included geometry aggregates and source references,
but did not preserve all actually supplied longitudinal bar coordinates,
per-bar steel refs, material laws or layout revision. They were therefore
insufficient for a standalone physical-input audit of the numerical result.

B5 adds an **immutable SectionInputTrace** to
`SectionCapacityResult`, captured **once** from the actual `RCSection`
supplied to the B1–B4 public `calculate_section` path. It carries:

- Section revision, width b/local-2 and depth h/local-3 in mm.
- Complete actual longitudinal bar list: stable bar identifier,
  x2/x3 in mm, diameter in mm and per-bar steel reference; concrete
  clear cover, tie diameter, layout revision.
- Concrete characteristic `fck`, design `fcd`, TS500 `k1`,
  `epsilon_cu`; source concrete revision.
- Every explicitly supplied design steel law (steel_ref, fyd, Es and
  revision), even when a law is unreferenced by a bar.
- Explicit source rule code, edition, rule ID and design material revision.
- Canonical UTF-8 JSON serialization and SHA-256 fingerprint.
  Bar and steel-law order are normalized by identifiers.
- A trace consistency check at result construction: section revision,
  material revision and captured serialized content must agree. A
  fabricated or stale digest/canonical JSON is rejected.
- Deterministic strict JSON and readable HTML project this **same**
  immutable trace and report the fingerprint scope clearly.

## Fingerprint boundary (critical)

`section_input_sha256` identifies **declared physical section/model inputs
only**. It does NOT attest to file authenticity, external authority,
code compliance or a real ETABS source. It is also NOT a whole-problem
fingerprint: frame, numerical policy, demand/request and external
source evidence records are not included. They are reported separately
under existing public result fields. A new physical cage or design
material will change the fingerprint even when section/revision labels
are mistakenly reused; this can help detect an inconsistency, not
prevent fraudulent data substitution.

No algorithm uses the digest as an engineering acceptance criterion.

## Regression and CI

- Two real supplied cages (4Ø20 and 6Ø20) show distinct fingerprints
  and complete coordinates. Bar reorder and mm/cm input routes yield
  identical canonical trace and **identical numerical result**, while a
  changed material law yields a different fingerprint.
- Strict report JSON and HTML agree on the exact bar IDs/positions,
  fck/fcd/k1/epsilon and steel law, plus source/method rev metadata.
- Input snapshot survives `UNSUPPORTED_MATERIAL`; no fabricated
  calculated capacity, and mutated SHA-256 or mismatched snapshot fails.
- B1–B4 numerical tests and the independent oracle remain unchanged;
  pinned `physics/section_capacity.py` remains byte-for-byte unchanged.
- The initial B5 CI revealed a legitimate equality regression: attaching
  a raw order-sensitive `RCSection` to result violated the earlier
  bar-reordering invariance. Fixed by making trace **value comparison**
  rely on exact canonical serialized data and digest rather than raw bar
  iteration order. A new negative/positive regression checks whole-result
  equality, without reducing the original assertion.
- After that repair, CI:
  https://github.com/feridunfc/Column/actions/runs/39830211097
  — four Python/OS jobs SUCCESS. The final example/docs commit receives
  a separate CI check.

## Reproduction (later local verification)

```powershell
python tools/check_architecture_contract.py
python -B -m unittest discover -s tests -v
python -B -m examples.section_pilot
```

User explicitly deferred local tests; do not require the user to run
these commands during Sprint B5. Running hosted CI is still mandatory.

## Non-acceptance

No new source-authentication resolver, live ETABS, TS500/TBDY full-column
approval, member mechanics, rebar candidate generation, shear, confinement
or design process is introduced. No constitutional amendment is silently
ratified; user-requested batched Supervisor review and procedural C-02
decision remain **OPEN / NOT ACCEPTED**. `main` remains unchanged.
