# B9 candidate — continuous concrete-block/bar overlap

**Status: implementation candidate; not independent acceptance.**

## Versioned source change

- Base `main`: `9269a00f5f5471ab68413c039912cafb2cf4db39`.
- Prior production kernel blob: `b2ac0114a5913e3088df6913de7537d7e0792b44`.
- New kernel blob: `13670adf184a906e059452b41cbf9e8b946e986b`.
- Production kernel reference: `Column/TS500-continuous-concrete-overlap-v1:tbdy_column_core/physics/section_capacity.py@13670adf184a906e059452b41cbf9e8b946e986b`.
- Scope is limited to the B9 fixed-axial root discontinuity in the existing rectangular-section model. This is a new kernel version, not a silent rewrite of the pinned source.

## Numerical defect and correction

The prior kernel subtracted the entire concrete stress times a bar's full area as soon as its centre crossed the equivalent concrete-block boundary. That binary predicate made the axial resultant discontinuous in neutral-axis depth (c). A target compression lying inside the jump had no root for that angular station; at 288 angular samples four stations were missing.

The new version subtracts the **actual circular overlap** between each longitudinal bar and the compression block. For a bar radius (r), signed centre distance (s=q_{bar}-q_{block}), the overlap is zero for (s\le-r), full for (s\ge r), and the circular-segment area for (-r<s<r):
[
A_{overlap}=r^2\arccos(-s/r)+s\sqrt{r^2-s^2}.
]
Its first moment is used to subtract the overlap at the correct centroid. The steel force is then evaluated as steel stress times steel area; concrete replacement is accounted for only in the concrete area.

For the supported model, increasing (c) expands the compression half-plane monotonically; after subtracting fixed bar disks, the net concrete compression area remains continuous and nondecreasing. Each bar strain is (\epsilon_{cu}(1-d/c)) with (d\ge0), so the capped monotone steel stress is nondecreasing. Thus the axial resultant is continuous and nondecreasing for this model, removing the prior bar-entry jump. The finite log scan remains a regression guard; it is not itself the mathematical uniqueness argument.

## Independent verification

- `tests/independent/oracle.py` independently reconstructs the clipped concrete region by strip integration and subtracts circular overlap with a separate oracle implementation.
- `tests/test_section_pilot.py` checks continuity at bar/block transitions, sampled axial monotonicity, fixed-(N) roots, and complete radial coverage at 288 angles.
- No tolerances are raised. The 1,000 Nmm angular budget is unchanged.
- The 72/144/288 convergence gate must still be assessed after the missing-root defect is removed; if successive differences exceed 1,000 Nmm, B9-F03 remains open and requires higher-resolution refinement.
- TS500/TBDY full-column compliance, C-02 ratification and G0/G1/G2 independent acceptance remain outside this patch.

**Release remains HOLD until exact-HEAD CI, high-resolution angular convergence and independent review.**
