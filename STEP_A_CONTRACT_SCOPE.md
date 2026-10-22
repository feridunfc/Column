# Step A (pre-G1 acceptance) — risk-focused contract notes

Base: `Column main@1cbb66aaea833b9cd5c141373b4537141006ca4c`.
Canonical v1.3.1 constitution/Worker/Supervisor files remain byte-for-byte unchanged.

- **C-08/09:** typed canonical N/mm/Nmm/MPa quantities and Angle; dimensional operations/overflow rejection and typed tolerances. No public float coercion.
- **C-10:** explicitly right-handed LocalFrame and 6-component physical ActionVector. Transform is `R*M + r x F` with r target-to-source. Axial kernel compression-positive sign mapping requires an enum, never guessed.
- **C-11:** StationRef identity is independent of StationGeometry length; ResponseKey carries typed step, run and generation.
- **C-12/14:** Provenance catalog is a supplied resolved-evidence interface, not an ETABS authority. Qualification is scoped to role/method/consumer/input revision, supported response semantics, expected population, exact run and generation, and cross-run receipts. No global `is_qualified`.
- **C-13:** producer, acquisition_mode, intended_use and response_semantics are different fields.
- **C-15:** Provided never means verified; NotRequired requires rule, requirement ID and applicability evidence *which is then resolved against method/consumer/revision*. Missing/Unsupported/Unresolved remain separate.
- **C-24:** PASS requires complete expected nonempty scope; a demonstrated FAIL can coexist with missing other scope. Freshness independent of compliance.
- **Domain import boundary:** no physical math kernel, ETABS, DB, HTTP or UI import.
- **B not yet authorized:** no kernel, adapter, application `calculate_section`, HTML or oracle migrated. Independent G1 review required first.

Numerical policy proposal and Worker start state are recorded outside the repo. A0/A test evidence is SHA-bound to a Worker commit, not a Supervisor acceptance or a TS500/TBDY design claim.
