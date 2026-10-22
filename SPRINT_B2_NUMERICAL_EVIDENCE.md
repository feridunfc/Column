# Column B2 — Numerical quality evidence (draft, 2026-10-22)

**Repository:** feridunfc/Column
**Base:** B1 `dd78097e98d4a64367f2060f5105f5facd00e9d7`
**Branch:** `worker/v131-b2-numeric-quality-20261022`
**Authority:** user requested batched Supervisor reviews after several sprints.
The process exception remains an OPEN C-02 change record; no independent G0,
G1 or G2 ACCEPTED status is implied by running this sprint.

## B2 scope and explicit deltas

1. **Axial root evidence:** For fixed-N at each neutral-axis angle, a
   359-sample logarithmic depth grid refines the original 180-point
   source scan by inserting geometric midpoints. Both pass through the
   unchanged legacy physics evaluator. Count sampled sign changes,
   samples within requested axial-force tolerance and smallest observed
   |N(c)-Ntarget|. More than one sign-change interval is reported as
   MULTIPLE_SAMPLED_ROOT_BRACKETS; a near-zero sample without sign
   change is recorded as NEAR_ZERO_WITHOUT_SIGN_BRACKET. Incomplete
   angles are retained as PARTIAL_ENVELOPE or NUMERIC_UNRESOLVED,
   not incorrectly classified as physical OUTSIDE_AXIAL_CAPACITY.
2. **Per-angle trace:** For a solved root, SectionState now carries
   sampled bracket count, scan sample count (359) and minimum absolute
   sampled residual as a typed Force. Same immutable result projects
   to strict JSON and the read-only HTML report.
3. **Undefined radial direction:** Two zero moment components produce
   UNDEFINED_MOMENT_DIRECTION before sampling any axial envelope;
   no NaN, Infinity, false radial capacity or expensive search.
4. **Angular discretization budget:** A separate opt-in
   `assess_radial_angular_refinement(problem)` computes coarse N-angle
   and fine 2N-angle radial capacities with the **same public section
   solver**, then compares observed |C_2N-C_N| to the typed
   `moment_tol + relative_tol*max(|C_2N|,|C_N|)`. It labels
   OBSERVED_DELTA_WITHIN_BUDGET, OBSERVED_DELTA_EXCEEDS_BUDGET,
   or UNRESOLVED; it never says converged exactly or TS500 PASS.
   This numerical budget is distinct from the N-root force residual.
5. **Regression tests:** Synthetic non-monotonic N(c) double-root and
   tangent-profile test doubles exercise the root scanner without
   modifying mathematical production kernels. Direct fixture confirms
   audit data present in JSON/HTML, and the no-scan zero-direction
   negative test. Coarse/fine radial numerical delta and incomplete
   resolution are independently exercised.

## Boundaries — retained rather than silently relaxed

- The source `physics/section_capacity.py` blob is unchanged.
- The independent oracle remains unchanged and test-only.
- **Sampling is not a global root-uniqueness proof**: arbitrarily
  narrow multiple roots and tangent points can still be missed between
  samples. No algorithm-level validation of all roots is claimed.
- A two-grid angular difference is an *observed numerical difference*,
  **not** a certified bound on error against a continuous limit.
- `COMPLETE_ENVELOPE` means all requested sampled angles supplied a
  qualified fixed-N state; see root_quality and scan diagnostics before
  interpreting it. It is never overall column-code compliance.
- No change to TS500 material strengths or strain models, no new
  normative acceptance criterion and no user-input tolerance widening.
- No ETABS integration, column/SCWB/stability/designer and no
  unconditional merge into main.
- Public invalid-input outcome handling and full C-01…C-32/AB-01…AB-18
  independent acceptance are still candidates for the batched review.

## Reproduction commands

```powershell
python tools/check_architecture_contract.py
python -B -m unittest discover -s tests -v
python -B -m examples.section_pilot
```

**Do not report B2 as G1_ACCEPTED or ACCEPTED_AB.**
