# Column v1.3.1 — B3 typed-input and angular-coverage sprint

**Date:** 2026-10-22
**Repository:** feridunfc/Column
**Baseline:** B2 `047646d046880e1c540810314ecdef683973499d`
**Worker branch:** `worker/v131-b3-api-validation-coverage-20261022`
**Supervisor:** Independent G0/G1/G2 pending. Batch-review request is a
documented OPEN C-02 process deviation; this is not accepted main.

## Implemented, bounded engineering contracts

1. **Explicit input validation alongside unchanged strict facade.**
   Existing `calculate_section(SectionCapacityProblem)->SectionCapacityResult`
   stays intact. New `validate_section_problem(candidate)` and
   `calculate_section_validated(candidate)` return typed
   `READY / INVALID_INPUT / UNSUPPORTED_INPUT` validation, with no false
   calculated result for malformed input, unsupported centroid reference,
   unsupported axial-sign convention or unsupported material law.
   This boundary only handles caller input and declared unsupported
   cases, **not** swallowed programming defects. The strict facade still
   rejects the unsupported tensile-positive convention explicitly.
2. **Exact sampled-angle coverage.** Immutable `AngularCoverage`
   stores attempted count, sorted resolved indices, sorted missing indices
   and computed completeness. It requires an exact partition of
   `range(angle_count)`; it cannot silently fabricate missing angles or
   duplicate an index. This is an *observed sample ledger*, not proof
   of a continuous failure-free interaction envelope.
3. **Fail-closed consistency.** A `COMPLETE_ENVELOPE` or
   `COMPLETE_RADIAL` result requires issue-free complete angular
   coverage with the expected number of retained states. Partial
   envelope has retained states and explicit missing angles. Direct
   strain-state has exactly one state and **no** envelope coverage.
   Unsupported material and undefined direction also carry no
   fabricated angle coverage.
4. **Same-result report provenance.** JSON and HTML show the exact
   angular coverage and source producer, source identifier, record
   identifier, declared input units, acquisition reference,
   namespace/identifier/revision. No new calculations are performed in
   reporting. Material and section revision are visible in both.

## Regression evidence

- Existing independent strip integration, multi-angle fixed-N/radial
  reference tests remain unchanged; pinned TS500 kernel and independent
  test-only oracle untouched.
- Five new tests: all-angle and one-angle-partial coverage incl.
  fabricated-complete rejection; public malformed/unsupported input
  boundary; JSON/HTML source provenance; no angular scan under an
  unsupported steel law; tension-positive axial sign rejected rather
  than silently used.
- CI run https://github.com/feridunfc/Column/actions/runs/39823814657
  on candidate head `870ca53b0e30ef36bf817bf30ca77230626950ee`:
  45 tests OK on Ubuntu 3.12/3.13 and Windows 3.12/3.13;
  architecture hash check and offline pilot examples passed.
- New optional API does **not** replace the C-19 original signature and
  is not an assurance of real external data's authenticity.

## Limits and remaining questions for independent Supervisor

- A live, independently authenticated ETABS provenance resolver is
  not present; input refs are declared and merely rendered.
- `COMPLETE_ENVELOPE` refers only to requested sampled angles. The
  B2 root scanner cannot certify all mathematical roots, and B2
  angular refinement only observes a coarse/fine difference.
- A forged domain instance via object-level bypass is a programmer
  invariant violation, not validated as user input.
- Native ETABS, member demand, second-order, shear, confinement, joint
  and candidate-generation engines are outside A/B.
- Full formal C-02 ratification, independent G0/G1/G2 dispositions,
  code-rule acceptance and merge into main are on HOLD.

## Local reproduction (PowerShell in an active venv)

```powershell
python tools/check_architecture_contract.py
python -B -m unittest discover -s tests -v
python -B -m examples.section_pilot
```

**Draft sprint candidate only. No merge, no column-code PASS.**
