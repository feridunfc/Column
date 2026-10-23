# C2 — Physical geometry / scenario / trial — development candidate

**Base HEAD:** `d33f5dba56ad71ff150353781c6607751ab019bf`, **base TREE:** `1e7996b463b381eeb7bf6852b9fb8f449c98bab8`.
**Clauses:** C-05, C-07, C-10, C-16, C-21, C-22; C-02/C-03 scope CR still proposed.

### Implementation
- `domain/scenario.py`: immutable, revisioned `DesignScenario` with explicit physical member census, supplied candidate assignment, analysis source roles and required scope. `TrialContext` is a single-target immutable candidate override; it never mutates source scenario or neighboring members.
- `engineering/member_mechanics.py`: bounded `MemberMechanics.prepare_geometry` only. `DeclaredLength` retains exact kind/source evidence and optional method reference. Centreline is computed from physical 3D ends. Clear, two unbraced and two effective lengths are separate fields; no storey-height/default I/J assumptions. Effective length requires explicit method reference but is never **qualified** in C2.
- Geometry output is `PHYSICAL_GEOMETRY_DECLARED_ONLY`, `stiffness_ready=False`, `second_order_ready=False` irrespective of supplied values. C3 is responsible for source-backed stiffness/stability qualification. No normative K/EI or P-delta formula is assumed.

### Gate
- Tests: `tests/test_c2_scenario_geometry.py` with positive and negative geometry/assignment/reference regressions.
- **No `check_column`, no PMM code PASS, no live ETABS, no code compliance**.
- C-02 change request remains NOT_RATIFIED. C2 is an isolated candidate until authorized versioned scope and independent Supervisor review.