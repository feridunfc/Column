# Column — TBDY Column Clean Start

Offline-first **TBDY/TS 500 RC column** engineering workbench. The project is deliberately narrow and does **not** yet certify a real ETABS column or a complete building.

## Open in Codespaces

Use **Code → Codespaces → Create codespace on main**. The devcontainer is Python 3.12.

```bash
python -m unittest discover -s tests -v
python -m examples.s1_demo
python -m examples.s1b_recorded_demo
python -m examples.s1c_demo
```

## Implemented

- **S1-H (work branch, UNTESTED):** source-pinned recovery planner routes 12 exact historical Column 235 evidence items to offline recoverability, project review, conditional existing-gateway acquisition, or downstream TS500/PMM computation. No ETABS live and no false design authority. See `S1H_SOURCE_RECOVERY.md`.
- **S1-G (actual archived Column 235 evidence):** original three-source SHA-256 audit; 60 observed historical force rows, 20 case/step populations and source-model/stability operand reconciliation, with real design explicitly BLOCKED. Public CI uses a derived ledger; the full actual archival ZIP is optional and user-supplied. See `S1G_ARCHIVED_SOURCE_AUDIT.md`.
- **S1-F (existing gateway replay consumer):** offline bridge accepts the old `etabs_gateway.replay.FixtureReplayProvider` public contract and old A18/A19/A20 typed materializations. It cross-checks α→k/Lk and signed I/J moment ratios; no ETABS COM and no real design authority. Codespaces CI currently uses a **contract fake** with the old gateway's genuine context fixture; original Python gateway package is *not* installed/executed by CI. See `S1F_GATEWAY_REPLAY.md`.
- **S1-E (synthetic source-bound mechanics basis):** original A18/A19/A20 pure kernels produce connected-member alpha, effective length k/Lk, signed I/J end moment ratios and two-axis slenderness/needed EI/Nk bases from typed evidence. Actual old native A17/A18 topology handoff and current 235 source proofs remain BLOCKED. See `S1E_SOURCE_BASIS.md`.
- **S1-D (provisional static mechanics):** migrated TS 500 minimum-eccentricity/slenderness kernels and **corrected a critical source-code error in moment magnification Eq.7.24/7.27**; signed-static synthetic-only end/interior composition with strict source and axis checks; NO real final N–M2–M3 qualification. See `S1D_MECHANICS_SCOPE.md`.
- **S1-C (station-preserving PMM path):** strict per-case expected station census (element, station, element station); retains physical intermediate stations and the governing point in passive reports, using the same previous PMM math. Native recorded records remain explicitly BLOCKED unless a true final-design demand compiler is implemented. See `S1C_ACCEPTANCE.md`.
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
