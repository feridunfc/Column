# B9 independent-review numerical observation (NOT an acceptance)

B9 CI source code at `b9bc32f8500354ff8bc669f9021869484aa7390c` produced the same 72/144/288 data in
Ubuntu Python 3.12 and 3.13. The Windows runner's CI jobs also
succeeded on this commit. GitHub Actions:
https://github.com/feridunfc/Column/actions/runs/39911340948

**Scope:** synthetic fixture 400×600 mm rectangular RC section,
6Ø20; N=500 kN; radial demand vector direction
(M2,M3)=(40,20) kNm; model TS500 strain compatibility source
`physics/section_capacity.py` unchanged.

```json
{
  "capacities_nmm": [
    264894954.85597295,
    264910256.12575525,
    264917904.34415603
  ],
  "angle_counts": [72,144,288],
  "observed_deltas_nmm": [15301.269782304764,7648.218400776386],
  "moment_budgets_nmm": [1000.0,1000.0],
  "verdict": "OBSERVED_NOT_STABLE",
  "independent_supervisor_acceptance": false
}
```

**Disposition:** blocker unresolved. Do not convert the dense oracle's
3% regression tolerance to a 1000 Nmm acceptance claim. No
`ACCEPTED_AB`, no engineering PASS, no merged main.

The B9 code/workflow runs `python -m examples.b9_numerical_review`
to regenerate this observation from the typed section-only public
solver. Capturing this observation does not constitute an independent
certification of the TS500 idealization.
