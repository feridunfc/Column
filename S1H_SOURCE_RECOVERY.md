# S1-H — Real Column 235 source recovery and future acquisition plan

**Implementation state:** Prepared on branch \`work/s1h-offline-evidence-recovery-20261021\`. **S1-H dedicated test suite added on the work branch; full original-archive gate requires operator-provided ZIP.** Do not merge to main / claim released until both offline CI and real source validation pass.

## Goal

Do **not** produce yet another synthetic PMM pass. Review the **original, unchanged** \`TBDY_COLUMN_EXTERNAL_AUDIT_2026-10-20.zip\`, identify what can be recovered now from archived/gateway records versus what requires further project-document review or eventual new ETABS capture. Existing gateway remains the only native data acquisition owner; **no live ETABS is performed**.

## Implementation

\`tbdy_column_core/s1h_recovery.py\` uses the S1-G actual 60-row archive audit plus six additional 2026-10-12/14 source artifacts. Nine original JSON blobs are verified with their exact SHA-256 hashes. Neither a hand-typed \`READY\` nor an uploaded substitute document can promote evidence. File paths and previous ETABS metadata do not authenticate current EDB bytes or analysis generation.

\`examples/s1h_recovery_plan.py\` prints machine-readable JSON and optionally writes a local copy.

### Source evidence and limits

- Historical \`Results.FrameForce\`: 60 old rows (12 single-valued, 48 extrema); **recorded EDB SHA != candidate EDB SHA**. This is historical reading only.
- Limited accepted native facts for the candidate from original ABI4/ABI5/ABI7: named \`Column_80x80\` section; \`I22/I33 = 0.03413333333333332 m^4\`; point 955 \`Global(74, 22.3, -5.15) m\` and point 758 \`Global(74, 22.3, 0) m\`. These are five source-scoped facts, **not** b/h, axis signs, releases or regulatory free length.
- October 14 user declares 800×800 mm and local-2 parallel Global X. Original \`review.status=NOT_RECORDED\`, local-axis signs missing. This can be reviewed against project documents OFFLINE.
- October 14 input authority matrix: 38 field values are null; 5 separately preserved limited native facts. First real project design was not computed.
- Native point distance 5150 mm is not the same assertion as archived unqualified \`ln = 4450 mm\`. The original coordinates say \`regulatory_ln=NOT_DERIVED\`.
- Original candidate B5/B6 \`None\`, current result epoch \`NOT_QUALIFIED\`; A17/global sway \`NOT_PROVEN\` and M6-B \`OPEN\`.
- Historical 86-column story action discrepancy +82,463.2776 kN, +42.4681% relative to sum of reported column compressions: unresolved **operand equivalence**. Neither result is accepted as design story shear.
- \`Grav_Ult\` first native M3 −28.6274508 kN.m and independent reported design M3 −171.5232 kN.m **do not share verified calculation semantics**.

## What can be done without ETABS

**Right now, with retained bytes:** pin original provenance; inspect all 60 historical raw rows; reconcile original native section/axes/coordinates within their historical/candidate scopes; compare old story operands; inventory old source producer code.

**With additional saved external artifacts:** review actual section dimensions, local-axis signs and free length against project drawings; hash exact candidate EDB file **without opening ETABS**; search for same-generation B5/B6, A17, A18, A19, A20 and spectrum/stability receipts already produced by the EXISTING gateway. Any recovered artifact must prove appropriate source and analysis generation before use.

**Only if matching original exports cannot be found:** defer further geometry, model/result, A17/story and modal M6-B native capture to a later **explicitly authorized existing gateway** session on Windows. No new reader or clone of COM gateway is authorized.

**Derived after inputs:** run A18→A19→A20, slenderness, second order and PMM using the already retained pure kernels. These computations are not themselves a reason to run ETABS if fully qualified upstream facts are on disk.

### Machine readable routes

\`S1HRecoveryPlan.items\` has 12 stable IDs:
- H01/H02: archived and scope-limited, historical only.
- H03: offline project-document review, no ETABS prerequisite.
- H04: offline exact candidate EDB bytes and same-generation export search, with future gateway only if missing.
- H05/H07/H08/H11: search any existing same-generation exports first, then future gateway if no acceptable source exists. **Gateway HOLD** remains.
- H06: reconcile incompatible story operands before sway use.
- H09/H10: derive with existing A19/A20 pure owners only after prerequisites.
- H12: final complete code/PMM gating; remains blocked.

The plan has explicit \`full_project_design_proven=false\`, \`source_models_rebound=false\` and \`etabs_live_executed=false\` in every output. Old application producer Python files appearing in the archive are included as **code inventory only**, never accepted as engineering result evidence.

## Usage (after test review)

\`\`\`bash
git fetch origin
git switch work/s1h-offline-evidence-recovery-20261021
python -m examples.s1h_recovery_plan /path/to/TBDY_COLUMN_EXTERNAL_AUDIT_2026-10-20.zip --output column235_source_recovery.json
\`\`\`

The original ZIP is not checked into GitHub; operator supplies it locally. No ZIP extraction or native process execution is performed; nine bounded pinned JSON member reads only.

## S1-H verification gates

The dedicated `tests/test_s1h_recovery.py` suite now covers 10 always-on contract/negative tests, plus 10 original-archive gates activated only by `COLUMN_S1H_SOURCE_ZIP`. Run the *real* ZIP tests on an authorized operator machine. Verify:
1. Exact original ZIP produces deterministic 12-item H01–H12 matrix and source digests.
2. All nine SHA pins verified. One-byte mutation, missing archive member, duplicate ZIP member, wrong EDB candidate all fail closed.
3. No user declaration / local path / arbitrary \`READY\` label unlocks current final design or present-day B5/B6.
4. Coordinates/inertia/five native facts reconcile, but no inferred TS500 free length from 5150mm physical joint distance.
5. Missing true matching external export never changes candidate generation; absence in this ZIP is not proof none exists anywhere.
6. No full-product PASS, no new gateway calls and no file mutation. Previous 112 tests must remain green on Python 3.12 and 3.13.

**Disposition:** S1-H implementation + dedicated test suite on work branch; CI and original-archive acceptance evidence required before merging. No live ETABS or column design release.


### PowerShell real-source test command

```powershell
$env:COLUMN_S1G_SOURCE_ZIP = $zip
$env:COLUMN_S1H_SOURCE_ZIP = $zip
python -m unittest discover -s tests -v
Remove-Item Env:COLUMN_S1G_SOURCE_ZIP
Remove-Item Env:COLUMN_S1H_SOURCE_ZIP
```

Do not commit the generated `column235_source_recovery.json` to the work branch; it is an operator output.
