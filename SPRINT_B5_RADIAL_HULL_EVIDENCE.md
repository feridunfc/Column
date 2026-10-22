# Column B5 — Radial sampled-hull geometry safety evidence

Date: 2026-10-22
Branch: `worker/v131-b5-radial-hull-safety-20261022`
Base B4: `3e1f750a82de911e5973b27c1f011fc47310d3ff`
Scope: v1.3.1 **given-cage, section-local, fixed-N** section numerical capacity only.

## Hazard addressed

The source-pinned legacy `radial_moment_capacity` intersects a ray from
the M2/M3 origin with the convex hull of **sampled** capacity states.
A ray/hull intersection by itself does not establish that the origin lies
inside the convex admissible region. If all sampled states lie on one
side of the origin, an apparent positive ray intersection must never
be advertised as an available radial capacity.

This is a safety/precondition guard around existing numeric math;
the TS500 strain-compatibility physics source and independent oracle
blobs remain unchanged.

## Implementation

- The pure `audit_radial_moment_hull` preflight checks origin containment
  by the maximum polar-angle gap between **non-negligible sampled**
  capacity vectors. Strict interior requires max angular gap < 180
  degrees (with a 1e-12 rad numerical boundary guard). Near-zero
  capacity points are conservatively excluded using the explicitly
  requested absolute Moment tolerance plus relative scale tolerance.
  All absolute/relative budgets retain their types/units.
- Empty/degenerate hull, a one-sided hull or an origin on the hull
  boundary returns status
  `DEGENERATE_SAMPLED_HULL` or
  `ORIGIN_NOT_INTERIOR_SAMPLED`. The outer
  `SectionCapacityResult` is **NUMERIC_UNRESOLVED**; no radial
  capacity or boundary is produced.
- Only after the strict-origin precondition does the unchanged
  legacy `radial_moment_capacity` run. The returned radius must be
  finite and strictly positive, and the returned M2/M3 boundary must
  align with the **positive** demand ray within the configured
  `moment_tol + relative_tol * radius` budget.
- `RadialHullEvidence` is immutable domain evidence: status,
  accepted/discarded sampled direction count, maximum angular
  gap, strict interior margin and optional boundary alignment
  residual in typed Moment units. Both JSON and HTML expose the
  same evidence without calculating physics again.
- `COMPLETE_RADIAL` now requires all three radial quantities,
  a positive radius, sampled strict-interior evidence and a
  boundary alignment residual inside the applied moment tolerance.
  A forged/incomplete `COMPLETE_RADIAL` object fails construction.
  Partial/unresolved status never publishes a radial capacity.

## Tests and exact observations

Nine new tests (48 + 9 = 57):
- Four cardinal sampled directions enclosing origin: geometry accepted.
- All moment vectors to one side: no interior, not capacity.
- Origin on hull boundary and collinear hull: no strict-interior claim.
- Near-origin vectors filtered by explicit Moment budget;
  nonfinite numeric samples rejected.
- Aligned and anti-aligned rays compared by an independently
  calculated `hypot` residual.
- Real 400x600 mm / six Ø20 fixed-N 72-angle fixture: radial
  origin containment evidence and passive JSON/HTML trace.
- Any attempt to forge a `COMPLETE_RADIAL` object with a missing
  radius/boundary/audit or over-budget ray residual is rejected.
- Injected synthetic full-angle yet one-sided moment states prove
  the old kernel ray function is **not called**.
- Injected wrong-sign kernel boundary result is rejected and
  never published as a radial capacity.

Code-head CI https://github.com/feridunfc/Column/actions/runs/39828713191
**57 tests PASS** on Ubuntu Python 3.12/3.13 and Windows
Python 3.12/3.13. Canonical doc/hash verifier and offline B1/B2 example
also PASS.

## Limitations (not engineering acceptance)

- The gap theorem provides a **finite sampled convex-hull
  precondition**. It cannot establish whether the real nonlinear
  section interaction region is convex or whether the continuous
  angle/strain state contains additional branches.
- The B2 axial-root scan is sampled, not an all-roots proof.
  In particular, undiscovered roots can invalidate the selected
  fixed-N branch even when the sampled hull surrounds the origin.
- The convex-hull interpolant is an approximation, not a certified
  exact radial capacity or full TS500/TBDY design check.
- A user choosing a moment tolerance larger than the entire
  capacity-vector magnitude may conservatively produce
  NUMERIC_UNRESOLVED, rather than a false positive.
- No new material law, member demand, ETABS source qualification,
  second order, reinforcement design, shear or confinement.
- No changes to the three canonical v1.3.1 documents or main.
  The user's multi-sprint/batched-Supervisor process decision remains
  an OPEN C-02 procedural deviation. Independent G0/G1/G2 have
  not been accepted; no main merge or code-compliance PASS.

## Reproduction (deferred user-side local verification)

```powershell
python tools/check_architecture_contract.py
python -B -m unittest discover -s tests -v
python -B -m examples.section_pilot
```

This document is a Worker evidence claim supported by CI, **not** an
independent Supervisor disposition.
