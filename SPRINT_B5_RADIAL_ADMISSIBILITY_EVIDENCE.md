# Column v1.3.1 — Sprint B5 radial-reference admissibility evidence

**Date:** 2026-10-22
**Base B4 HEAD:** `3e1f750a82de911e5973b27c1f011fc47310d3ff`
**Branch:** `worker/v131-b5-radial-admissibility-20261022`
**Technical test run:** https://github.com/feridunfc/Column/actions/runs/39830321182

## B5 bounded engineering finding

The pinned numerical helper `radial_moment_capacity` performs a forward
ray intersection with its convex hull of sampled `(M2,M3)` states.
A ray from the origin can encounter a positive **entry intersection**
even if `(0,0)` itself lies **outside** the sampled convex hull.
This cannot be silently interpreted as an admissible radial section
capacity from the origin.

A deterministic negative test constructs a positive-quadrant triangle,
executes the **original** kernel, confirms it returns `PROVEN` with
a positive ray intersection, and independently refuses the hull as
radially admissible.

## Implemented / tested

1. `check_radial_reference(states,policy)` derives a convex polygon
   from only already-solved sampled moment states. The origin must be
   strictly inside all oriented hull half-planes with a **positive
   perpendicular clearance greater than the explicit absolute Moment
   tolerance**. Any degenerate, nonfinite or outside/on-boundary hull
   yields a typed unresolved state. Clearance is expressed in Nmm.
2. `verify_radial_boundary` independently verifies any returned
   radial capacity has finite positive magnitude, is in the declared
   moment direction within the separately dimensioned Moment/relative
   tolerance, and lands on a segment of that same sampled hull within
   the same declared numerical budget. The pinned physics function is
   still responsible for computing the intersection.
3. `SectionCapacityResult.radial_reference_audit` retains the status,
   sampled hull vertex count, minimum signed origin-to-edge clearance
   and required clearance. `COMPLETE_RADIAL` is refused without a
   validated origin and finite positive capacity plus both components.
   Other statuses cannot carry a fabricated radial capacity.
4. When all axial angles are solved but radial origin or boundary
   geometry fails, the result is `NUMERIC_UNRESOLVED`, retains the
   solved section states and full sampled-angular coverage, and has
   `radial_capacity=None`. It is **not** physical structural FAIL
   or `OUTSIDE_AXIAL_CAPACITY`.
5. JSON and HTML render only the same immutable result, including
   admissibility status, signed clearance and unresolved issues.
6. Five B5 tests cover the legacy positive entry intersection,
   strictly interior polygon, origin on boundary, collinear hull,
   false kernel boundary injection, production fixture metadata, and
   end-to-end public `calculate_section` refusing a synthetic
   outside-origin hull **without invoking radial calculation**.

**Exact-head CI:** Ubuntu Python 3.12/3.13 and Windows Python 3.12/3.13
each passed **53 tests**, `ARCHITECTURE_CONTRACT_OK`, and the B1/B2
offline examples at `8a95c511b8fb5d6fe0e48fb0269ad2987ffc3af6`.

## Hard limitations / acceptance hold

- This is a **fail-closed sampled-hull geometry guard**, not an
  independent normative interaction-surface model. It cannot certify
  the global root count, that every curve branch was sampled, or
  continuous-angle convergence.
- It is deliberately conservative for an origin outside or near the
  sampled moment polygon; a separate engineering treatment of
  off-origin interaction geometry may be necessary.
- No modification to the SHA-pinned `physics/section_capacity.py` or
  independent oracle file; no change to material strength values,
  strain assumptions, or concrete stress block.
- No live ETABS, column member demands, amplification, confinement,
  reinforcement selection, shear, or full TS500/TBDY PASS.
- The canonical three v1.3.1 documents and `main` remain unchanged.
- Operator's batched-sprint review is recorded as **open C-02 process
  deviation**; independent G0/G1/G2 acceptance is still required.
  A green CI only establishes technical test results.

## Local reproduction (when user chooses to run tests)

```powershell
python tools/check_architecture_contract.py
python -B -m unittest discover -s tests -v
python -B -m examples.section_pilot
```
