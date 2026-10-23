# Column v1.3.1 — B4 frame policy / report trace evidence

Date: 2026-10-22
Base: B3 `49d0c75c85aefb12dd97731ddb6137bff1555acd`
Branch: `worker/v131-b4-frame-policy-audit-20261022`

## Scope and implementation

B4 preserves the numerical TS500 section kernel, oracle, section API,
physical layout and immutable v1.3.1 canonical documents. Its scope is
**explicit source-local coordinate-frame precision** and result reporting.

1. A pure `frame_basis_max_residual(LocalFrame)` derives the maximum
   norm, pairwise-orthogonality or handedness deviation (dimensionless).
   `LocalFrame` already enforces its own construction tolerance; B4 adds
   verification against the independent user-supplied
   `NumericalPolicy.axis_tol`.
2. The strict `calculate_section(problem)` path now rejects a frame
   whose deviation exceeds the applied numerical policy with
   `FRAME_EXCEEDS_REQUESTED_AXIS_TOLERANCE`. The optional typed
   `validate_section_problem` yields `INVALID_INPUT` with the same
   reason instead of computing a misleading section result.
3. Every result, including partial or numerically unresolved ones,
   preserves the full `FrameModelContract` and observed basis maximum
   residual, validated against the applied policy.
4. Passive JSON/HTML projection of the *same* result includes local
   frame reference, explicit axial sign, global origin (mm), local
   e1/e2/e3 basis components, observed precision and requested
   axis-tolerance budget. Reports do not recalculate transformations.
5. Invariance regression: changing only a valid global placement and
   orientation of the declared local frame leaves a section's
   already-local N/M2/M3 numerical values unchanged, while both
   reports accurately trace the different frame.
6. Regression rejects a frame that is valid under its own
   LocalFrame tolerance, but is not accurate enough for the tighter
   numerical-policy axis tolerance. Relaxed policy is a *deliberately
   changed explicit input*, not an automatic hidden relaxation.

## Strict engineering limits

- A/B uses **section-local** bar coordinates, neutral-axis angles,
  N and M2/M3 directions. It does not interpret or transform external
  ETABS/global force records on behalf of the caller.
- This is not a new general global-to-local response compiler. The
  existing `transform_action` with physical `r x F` remains its
  separate domain operation; C-21 member-demand compilation is future scope.
- A nonzero global frame origin is **not** automatically an eccentric
  section. The reference remains `SECTION_GEOMETRIC_CENTROID`;
  a global translation cannot justify inventing a transferred moment.
- The section solver still refuses a tensile-positive F1 sign
  convention without an explicit mapped input.
- The sampled dual-grid axial-root scan and measured coarse/fine
  angular difference are not global root uniqueness or certified
  angular truncation-error proofs.
- No normatively approved RC column, no shear/confinement/second
  order/design of steel, no native mutation or data-store.
- The user requested multi-sprint development then one independent
  Supervisor review. Formal C-02, G0/G1/G2 and merge into main
  remain **OPEN / NOT ACCEPTED**; CI is only technical evidence.

## Reproduction and observed CI

```powershell
python tools/check_architecture_contract.py
python -B -m unittest discover -s tests -v
python -B -m examples.section_pilot
```

Code commit CI:
https://github.com/feridunfc/Column/actions/runs/39825482540

All **48 tests** passed in each of: Ubuntu Python 3.12 and 3.13;
Windows Python 3.12 and 3.13. Three canonical document SHA-256
verification and the offline B1/B2 examples passed.

Full source integration and independent Supervisor acceptance
remain separate from test results.
