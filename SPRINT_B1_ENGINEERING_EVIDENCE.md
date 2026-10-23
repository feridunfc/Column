# B1 sprint engineering evidence / acceptance ledger

## Anchors and authority

- Base: `17161466e2e633f6155626054bff1ea9ffe61af5` (A0+A; 22/22 tests).
- B1: first explicit **given-cage section capacity pilot** on draft-only
  `worker/v131-b1-section-pilot-20261022`.
- Original kernel blob `b2ac0114a5913e3088df6913de7537d7e0792b44`
  is preserved exactly (TS500 strain compatibility for rectangular RC).
- Test-only independent oracle blob
  `4b78e7bd83e1ed31d3ac006122e5e499499c7e9b` preserved exactly.
- `physics/rebar_layout.py` contains **only** the frozen ColumnBarPoint
  dataclass dependency. No rule-based reinforcement candidate generator.
- Three canonical documents on main and this sprint branch remain
  byte-for-byte pinned to v1.3.1.
- C-02 sprint batching change **awaits formal versioned ratification**; this
  work is candidate/provisional and is NOT G1_ACCEPTED or ACCEPTED_AB.

## B1 scope and acceptance evidence

- Three distinct requests: `AtStrainState`, `EnvelopeAtAxialForce`,
  `RadialCapacityAtAxialForce`.
- The actual supplied bar centres, bar IDs, and steel references enter
  the same source-pinned capacity kernel via one adapter.
- Material model inputs are explicit: C35 fck=35, fcd=35/1.5,
  k1=0.79, epsilon_cu=0.003; longitudinal steel design fyd=420/1.15,
  Es=200000 MPa. Source material and law revisions are explicit.
- Fixture A: 400x600 mm, four Ø20 bars at (±150,±250) mm.
- Fixture B: A plus Ø20 at (-150,0) and (+150,0) mm.
- Second section: 450x650 mm, B placement offset 50 mm from outer faces.
- Cover is 30 mm concrete-to-exterior tie; Ø10 mm tie; no automatic
  TS500 clear-spacing assessment is claimed.
- Unit-safe canonical quantities, 6-component physical source/reference
  transformation and response identity remain in A contracts.
- Independent Gauss-Legendre strip integration tests 3 direct states
  per cage; independent all-bracket root tests fixed-N samples; dense
  independent radial reference and 72/144/288-angle convergence tests.
- For every numerical fixed-N solution, applied `max_iterations` is sent
  to the single-angle legacy root solver; actual N residual is compared
  with the requested dimensional force and relative policy.
- Root sign-bracket census is **sampled, not mathematical proof**:
  multiple/bracketless cases cause unresolved outputs. The old helper
  `build_interaction_envelope_at_axial_force` is not used because it
  does not accept max_iterations.
- Missing numeric root/partial envelope is NOT declared physically
  outside capacity. The zero-direction request is explicitly undefined.
- Mixed bar constitutive laws are UNSUPPORTED (rather than silently
  substituting one fyd/Es). Reordering bars preserves results via stable
  canonical order.
- JSON and HTML are passive renderings of the same result payload;
  strict JSON forbids NaN/Infinity. There is no `ColumnResult`
  or code compliance PASS in this sprint.

## Provisional tolerances in the B1 test harness

- Independent direct strain-state: ΔN <= 1 N; ΔM2/M3 <= 2000 Nmm.
- Target-N residual: <= requested 1 N, without hidden relaxation.
- Radial dense-reference delta <= 3% and angular 144/288 delta <= 3%.
  These are **test tolerances**, not TS500 acceptance factors. A later
  independent Supervisor must review convergence evidence and budget
  before engineering acceptance; tolerances may not be widened to hide
  failures.

## Unsupported / deferred

- No full proof of globally unique capacity root (sampled bracket count
  alone cannot detect every tangency); user-facing `root_quality`
  explicitly marks this limitation.
- No public validation outcome type for all malformed section
  constructor inputs (currently typed constructor errors).
- No native ETABS/recorded analysis qualification, member demand,
  second-order, shear, confinement, SCWB/joints, candidates or
  column-code PASS.
- No datastore, optimizer, FE model mutation or UI.
- Full C-01…C-32 and AB-01…AB-18 independent acceptance ledger remains
  for the batched Supervisor review. Tests are not that disposition.

## Commands

```bash
python tools/check_architecture_contract.py
python -m unittest discover -s tests -v
python -m examples.section_pilot
```

**No merge to main, and no false `G1_ACCEPTED` / `ACCEPTED_AB`.**
