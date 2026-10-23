# B6 — fixed-N root and angular-refinement engineering evidence

Base B5 `a8e623beafc9362af991aab9a67e059a14d3d19e`.
Code HEAD `9e279571bbcfdfd3224cb8bd3f74d4caf3402d88`.

Implemented:
- 359-point log-depth grid records every **sampled sign-change interval**.
- The source solver's reported c must occur within the detected single
  crossing interval, not merely have a small residual at a different c.
  Multiple sample crossings, missing roots or inconsistent source c are
  fail-closed numerical states; retained resolved angles are not discarded.
- `assess_three_level_radial_refinement` supports configurable increasing
  counts (default 72/144/288) and separate observed 72→144,144→288
  Moment differences and Moment budgets. Absent radial states yield
  `NUMERIC_UNRESOLVED`. Existing two-grid API remains unchanged.
- New tests mock a false c with a perfect N residual, and check the
  8/16/32 mathematical differences, negative count order and
  unresolved max-iterations path.

Limits: The discrete scan cannot prove root uniqueness between points.
Even a 72/144/288 observed stable delta cannot rigorously bound the
continuous-section capacity error. The pinned kernel is unmodified.
The model's bar-centre concrete displacement and convex hull are not
certified by these extra tests. No full-column code approval.

CI: https://github.com/feridunfc/Column/actions/runs/39910108649
Python 3.12/3.13 on Ubuntu and Windows successfully completed.
Supervisor G0/G1/G2 and C-02 ratification remain OPEN.
