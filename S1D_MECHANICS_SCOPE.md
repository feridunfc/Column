# S1-D — TS 500 minimum eccentricity / slenderness / magnification

**Status:** source-migrated static calculation kernels and **synthetic-only mechanics preview**. **Not** a qualified final design-demand producer. Live ETABS **HOLD**.

## Source-preserving reuse

Three pure original TBDY modules are now in `tbdy_column_core/physics`:
- `minimum_eccentricity.py` original Git blob `ed5f218d42dcfa71f380f52e3e037117d75cdb22`
- `slenderness.py` original Git blob `35fab7621d0e381fd762a6d75a240a55fe685943`
- `moment_magnification.py` original Git blob `8bd6ab3bd97a47b99f9284debdfac8159de58845`

Only module namespace references were adjusted, not the original engineering formulas. Original A19–A22 source promotion pipeline and ETABS COM were not copied.

`preview_ts500_static_mechanics()` evaluates prequalified **synthetic, raw first-order, signed-static** demand states:
1. Requires explicit physical I_END/J_END identities; a historical `STATION` row cannot be guessed to be a column end.
2. Requires typed `ColumnSlendernessBasis` for both local axes; missing M1/M2, free length, k or sway => block.
3. If moment magnification is required, demands must have a matching M2/M3 typed basis, compatible Nd, l_k, i and sway status. No unconstrained default magnification.
4. Applies existing source TS 500 magnification kernel per concurrent state/axis only in a **numerical preview**.
5. Applies existing minimum eccentricity to qualified end states only, preserves interior station force states independently, and branches ± when a minimum moment has zero sign.
6. Produces neither a PMM design PASS nor a report authorizing final N–M2–M3; `final_design_demand_proven=false` permanently.

**Important engineering issue:** The relative order of second-order amplification, end minimum eccentricity and ETABS-already-applied effects has not yet been independently reconciled against the governing design conditions. Preview arithmetic is therefore intentionally NOT automatically wired into `S1ColumnSnapshot.FINAL_DESIGN_REVIEWED`. Kernel regression tests alone do not resolve M6-B modal semantics or verify free length, end conditions and sustained-load/stiffness facts.

## Remaining S1-D blockers before real column 235

- An upstream producer for `ColumnSlendernessBasis`, verified physical end mapping, l_n, k, signed M1/M2, sway classification, horizontal-load-between-ends, EI/Nk, creep, and correct case generation.
- TS 500 source-based independent checks of the exact code algorithm and composition/ordering. The retained old kernel is a code baseline, not guaranteed regulation truth.
- Reliable complete registered combined-load and station universe; signed static vs RS/envelope semantics.
- Confirmed current model fingerprint and analysis generation and second-order treatment in ETABS model/results.
- A typed final design-demand compiler after those proofs; only it may unlock `RECORDED_ETABS` PMM.

To run: `python -m unittest discover -s tests -v`.
