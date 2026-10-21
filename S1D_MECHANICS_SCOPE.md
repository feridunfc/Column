# S1-D — TS 500 minimum eccentricity / slenderness / magnification

**Status:** source-migrated static calculation kernels and **synthetic-only mechanics preview**. **Not** a qualified final design-demand producer. Live ETABS **HOLD**.

## Source-preserving reuse

Three pure original TBDY modules are now in `tbdy_column_core/physics`:
- `minimum_eccentricity.py` original Git blob `ed5f218d42dcfa71f380f52e3e037117d75cdb22`
- `slenderness.py` original Git blob `35fab7621d0e381fd762a6d75a240a55fe685943`
- `moment_magnification.py` original Git blob `8bd6ab3bd97a47b99f9284debdfac8159de58845`

The initial migration changed module imports only. **Independent source checking exposed a real error in the old Eq.7.24/7.27 kernel**: `1 - Nd/(1.3 Nk)` rather than the TS500 Turkish `1 - 1.3 Nd/Nk`. The mathematical expressions have now been corrected in the clean repo, with frozen numeric regression tests (and a clear record that the old kernel had this bug). The original A19–A22 source promotion pipeline and ETABS COM were not copied.

Primary references:
- TS500 Turkish Feb 2000 Eq.7.24/7.26/7.27 (public mirror): https://www.yumpu.com/tr/document/view/39327047/ts-500-atalarscom/34
- Licensed English translation, PDF page 38 Eq.7.24/7.26: https://staff.emu.edu.tr/cemalgenes/Documents/courses/Civl471_2019_20_Spring/330321606-TS-500-English-Version.pdf
- Ozmen/Girgin/Darilmaz (2015) worked numerical Eq.7.27 beta_s=2.185: https://dergipark.org.tr/tr/download/article-file/284890

**Translation caveat:** English PDF Eq.7.27 visually omits 1.3, whereas the Turkish text and independent Turkish numerical example include 1.3. The code follows the original Turkish provision. Formal release shall confirm the licensed authoritative Turkish standard and the exact design edition. English translation alone must not override the Turkish clause.

`preview_ts500_static_mechanics()` evaluates prequalified **synthetic, raw first-order, signed-static** demand states:
1. Requires explicit physical I_END/J_END identities; a historical `STATION` row cannot be guessed to be a column end.
2. Requires typed `ColumnSlendernessBasis` for both local axes; missing M1/M2, free length, k or sway => block.
3. If moment magnification is required, demands must have a matching M2/M3 typed basis, compatible Nd, l_k, i and sway status. No unconstrained default magnification.
4. Applies TS500 Eq.6.16 minimum-eccentricity MOMENT FLOOR to the qualified physical end states **before** Eq.7.26 moment magnification, preserving interior stations as-is. ± sign branches remain attached to each source state.
5. Applies the corrected Eq.7.24/7.27 magnification factors independently to each required axis and each branch, only in a **numerical preview**.
6. Produces neither a PMM design PASS nor a report authorizing final N–M2–M3; `final_design_demand_proven=false` permanently.

**Important engineering issue:** The minimum-eccentricity floor before TS500 Eq.7.26 magnification has been corrected. However its composition with ETABS-already-applied effects, sway/global amplification and real load-generation semantics remains unqualified. Preview arithmetic is therefore intentionally NOT automatically wired into `S1ColumnSnapshot.FINAL_DESIGN_REVIEWED`. Kernel regression tests alone do not resolve M6-B modal semantics or verify free length, end conditions and sustained-load/stiffness facts.

## Remaining S1-D blockers before real column 235

- An upstream producer for `ColumnSlendernessBasis`, verified physical end mapping, l_n, k, signed M1/M2, sway classification, horizontal-load-between-ends, EI/Nk, creep, and correct case generation.
- TS 500 source-based independent checks of the exact code algorithm and composition/ordering. The retained old kernel is a code baseline, not guaranteed regulation truth.
- Reliable complete registered combined-load and station universe; signed static vs RS/envelope semantics.
- Confirmed current model fingerprint and analysis generation and second-order treatment in ETABS model/results.
- A typed final design-demand compiler after those proofs; only it may unlock `RECORDED_ETABS` PMM.

To run: `python -m unittest discover -s tests -v`.
