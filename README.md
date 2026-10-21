# Column — TBDY Column Clean Start

Offline-first **TBDY/TS 500 RC column** engineering workbench. The project is deliberately narrow and does **not** yet certify a real ETABS column or a complete building.

## Open in Codespaces

Use **Code → Codespaces → Create codespace on main**. The devcontainer is Python 3.12.

```bash
python -m unittest discover -s tests -v
python -m examples.s1_demo
python -m examples.s1b_recorded_demo
```

## Implemented

- **S1-B (bounded read-only ETABS bridge):** use the unchanged original TBDY ColumnForceResultPopulationFact from the verified Windows provider, with explicit unit and force-row conversion, exact case/column/station retention, and no automatic PMM promotion. The tracked historical 235 fixture contains only three genuine Grav_Ult rows from the earlier 60-row archive. See ETABS_ADAPTER_HANDOFF.md.
- **S0:** TS 500 Eq. 7.13 non-sway screening for a **complete, qualified, signed linear-static** story state.
- **S1 — offline numerical seed:** rectangular column perimeter bar geometry; C16–C50 source-supported concrete-strength block factors; strain-compatible 3D N–M2–M3 section capacity; deterministic selection of a longitudinal candidate from a **complete, explicitly reviewed static I/J-end demand universe**; passive JSON/hash reporting.
- Pure math owners were retained from **feridunfc/TBDY**, frozen blob-identical at historical `main@1440df1` and local `b43b2e2` (package import names adjusted). The independent strip integration oracle also comes from the former repository.
- The code fails closed on unsupported modal/envelope demands, missing design-basis reviews, incomplete I/J pairs, mixed source/epoch/generation and incompatible case identities.

### Critical limitations

The demo uses **SYNTHETIC** signed-static demands. No current B-BLOK/235 native design-force records have been imported, and no ETABS COM operation is performed. In S1, `FINAL_DESIGN_REVIEWED` plus `basis_refs` is a **declaration from upstream**, not a proof that minimum eccentricity, second-order effects and the design-combination scope are truly resolved. Without that upstream verification, use `RAW_FIRST_ORDER`; numerical selection is blocked.

I/J endpoints are the current narrow demand coverage; physical intermediate stations (e.g. those in the recorded 235 run), ETABS combination lineage, minimum eccentricity, full biaxial second-order interactions, longitudinal detailing, confinement, shear, beam-column joints and modal earthquake treatment still need independent product-level acceptance. No numeric result is marked a full TBDY code PASS. **ETABS live HOLD** remains.

## Next acceptance step

Build a recorded **read-only** ETABS fact adapter and independently qualify each final design case/state, station population, source fingerprint, member axes, demand transformation and selected-rebar interface. Then bind the full actual demand population (including required interior stations), not an operator-supplied `reviewed_*` fixture. Only after this can S1 real-project acceptance be assessed.

See `INTEGRATED_ARCHITECTURE.md` and `SPRINT_0_SUPERVISOR_TASK.md`.
