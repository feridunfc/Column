# S1-E — effective length, physical end-moment and slenderness fact producer

**Status:** OFFLINE NUMERICAL PRODUCER (synthetic provenance only); live/recorded real-column acceptance **BLOCKED**. ETABS LIVE HOLD.

## Reused original, no duplicate TS500 physics

Two pure source modules from `feridunfc/TBDY` (historical main 1440df1), import namespace changed only:
- `tbdy_column_core/physics/effective_length.py`, source Git blob `c1ac999a9d8ca3ffa3999e83507b4cc1a0290724`: TS 500 Eq.7.16 connected-member α, Eq.7.14–7.15 k and `Lk=k ln`.
- `tbdy_column_core/physics/end_moment_ratio.py`, source blob `e80dad66e6bc37afe9f41e24694198ba00cd5504`: signed same-case I/J M1/M2 ratio on qualified static exact data.

Retained S1-D `physics/slenderness.py` and `physics/moment_magnification.py` are reused, **including the previously corrected TS 500 beta denominator**.

## What the new producer computes

`tbdy_column_core/s1e_basis.py::prepare_s1e_basis` joins typed evidence in this order:

1. Exact model fingerprint, epoch, analysis generation, case/axis and source-bound physical I/J role.
2. Qualified member inertia, length, TS500 effective inertia factor (A18 provenance) → both ends' connected-beam/column α.
3. Qualified free length and exact local-axis sway fact (A17/A19 provenance) → local M2 and M3 `k`, `Lk`.
4. Same static output case, same original source, actual signed I/J N–M2–M3 states → each axis' ratio `M1/M2` (A20 source math). Interior states are retained; they cannot be assigned I/J merely based on the station number.
5. Per-case, per-axis `ColumnSlendernessBasis` and numerical slenderness disposition. If required, per-state axis basis for effective EI/Nk and moment magnification, *without applying or approving PMM*.

This is a **small producer**, not an alternative PMM or a new ETABS API. `ColumnSlendernessBasis` can feed the existing S1-D synthetic preview. Exact M2/M3 statuses are separate. Sway permitted / TS 500 story ΣNd/ΣNk / modal M6-B is intentionally blocked.

## Explicit limits

**Important:** `S1EAxisFacts` is the input contract for the old A17/A18/free-length/stiffness producers. In Codespaces, those facts can currently be instantiated for synthetic verification only. Supplying nonempty `source_ref` strings or toggling `one_end_hinged` does not establish a current real ETABS source. This initial S1-E does **not** read current Windows topology, prove the native A18 producer output, or certify B-BLOK free length from the 515 cm joint distance or 445 cm station extent.

- `SourceClass.RECORDED_ETABS` is unconditionally fail-closed pending a verified old-provider/gateway handoff.
- S1-E does not infer source native load combinations, modal simultaneous results or global axes from local axes.
- S1-E's synthetic no-sway examples are *numerical verification*, not governing building-design assumptions.
- Old A18/A19 have substantial dependencies on topology, section inertia, end releases and local-axis evidence; copying their full application graph into this minimal repository would defeat the architecture. Reuse them through an explicit **read-only typed provider handoff** on an authorized Windows worker after source/epoch checks, not a second COM stack.

## Remaining production integration

1. Consume a current **native A18/A17/local-topology/physical-end/free-length** product from the existing ETABS gateway with model/epoch and generation evidence. Must include all connected beams/columns and qualified end offsets/support.
2. Check the complete per-case signed static I/J and intermediate station population, local/global axes, axial demand selector and actual load-combination semantics.
3. Build stiffness/creep and second-order state from documented normal force history; no default horizontal load `False`.
4. Validate real-source producer with two distinct columns; full model scope and modal M6-B remain separate mandatory engineering acceptance.
5. Only after verified final design-demand calculation may real records enter PMM numerical candidate selection. **Current release remains blocked.**

## Evidence classification

- Existing S0–S1-D tests: retained.
- New S1-E tests: producer k/Lk/α, signed M1/M2, per-case two axes, S1-D synthetic application, missing facts/old native refusal.
- This document does not claim imported live topological facts or an authoritative source-certified k and Lk for column 235.
