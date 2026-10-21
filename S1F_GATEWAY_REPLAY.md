# S1-F — existing ETABS Gateway, **offline only**

**Actual code status:** pure replay-consumer implemented and regression-tested. No Windows ETABS required or used. No new COM transport/gateway/client has been created. Real-column design acceptance: **OPEN / BLOCKED**.

## Reuse and ownership

The existing gateway remains the owner:
- `feridunfc/TBDY/packages/etabs_gateway/src/etabs_gateway/replay.py` — `FixtureReplayProvider` with `.fixture`, `.fingerprint`, `.read_context()`.
- `tbdy_engine/application/column_a18_end_restraint.py` — `A18EndRestraintMaterialization` with READY α and source refs.
- `tbdy_engine/application/column_a19_effective_length.py` — `A19AxisEffectiveLengthMaterialization` with READY k, Lk and sway.
- `tbdy_engine/application/column_a20_end_moment_ratio.py` — `A20AxisEndMomentMaterialization` with exact signed concurrent I/J evidence.

The new `tbdy_column_core/s1f_gateway.py::reconcile_existing_gateway_replay()` **accepts these existing objects** as injected dependencies, without importing COM or invoking ETABS. Original TS500 `effective_length.py` and `end_moment_ratio.py` pure owners recalculate numerical consistency checks; no new physics formula is introduced. 

## Checks

1. Gateway fixture schema/type, fingerprint continuity, replayed immutable context, model path and unit metadata.
2. Exact A18 population: 2 axes × bottom/top; READY+original authority; α consistent with recorded Σ(I/L) column numerator and beam denominator.
3. Exact A19 population: 2 axes; READY+authority; original α, k, Lk and sway consistent with the existing pure length kernel.
4. Exact A20 population: each listed signed-static case × M2/M3; READY+authority; same qualified I/J state identity, signed moment values, curvature and ratio verified by the *existing* ratio kernel.
5. No positive path sets `edb_bytes_verified`, `analysis_generation_verified` or `real_design_basis_verified` to true.

## Codespaces usage

```bash
python -m unittest discover -s tests -v
python -m examples.s1f_demo
```

The example and CI use the **genuine old gateway fixture JSON** (`tests/fixtures/existing_gateway_context_v1.json`, source old `packages/etabs_gateway/tests/fixtures/gateway_context_v1.json`) plus an explicitly synthetic A18/A19/A20 **contract fake**. The context fixture's canonical SHA is checked, but **the original `etabs_gateway` Python package is NOT imported or exercised in this Codespaces CI**. Tests therefore demonstrate compatibility with the published interface, not that a Windows gateway export ran or that a historical engineering project was accepted.

When the old gateway package is available on an offline machine, pass an original `FixtureReplayProvider.from_path(...)` object directly into the S1-F function. The old A18/A19/A20 outputs must come from the same preserved acquisition/result epoch. Do not try to establish those facts using arbitrary source-ref strings.

## Critical unmet source proof

**Gateway context SHA-256 fingerprints the fixture context metadata, NOT EDB file bytes or ETABS analysis.** The original legacy A18/A19/A20 dataclasses carry source refs but no cryptographically authenticated current model / epoch / generation inside these objects. The offline reconciliation therefore cannot confirm that a tuple of records came from the same current ETABS model. Hardcoded `READY` or a fake ref does not establish external trust.

Still needed for real Column 235:
- full historical-to-current EDB fingerprint and memory/live consistency;
- gateway-acquired case/step/station/column expected census;
- A17 sway and A18 physical end/release/axis/connection proof with A19 free length and current generation;
- A20 real signed-static exact same-generation I/J demands;
- final design demands including min eccentricity and 2nd order, validated against code rules;
- native/live source acquisition later when it becomes possible.

**Outcome:** `REPLAY_RECONCILED_NO_LIVE_PROOF` means the *replayed recorded numbers are internally consistent*, not engineering compliance. ETABS live HOLD.
