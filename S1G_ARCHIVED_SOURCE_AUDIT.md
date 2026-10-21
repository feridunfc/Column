# S1-G — Kolon 235 historical source audit

**Observed source:** exact user-supplied `TBDY_COLUMN_EXTERNAL_AUDIT_2026-10-20.zip` from the old TBDY project. This code does NOT connect to ETABS or establish a current result epoch. Source identity is enforced by **3 original SHA-256 digests** in `tbdy_column_core/s1g_archive.py`.

The original 35,925-byte 19 October recorded inputs JSON is **not included in the public repository**. It remains in the user's prior local ZIP. The JSON ledger in `tests/fixtures/column235_s1g_archived_evidence.json` is a derived, bounded read-only summary; it is not the original source. Neither a hand-built summary nor a three-row fixture can prove the full model's combination/station universe.

## Findings from the ACTUAL 60 archived rows

- 20 observed case/step populations × 3 output stations = **60** factual rows; 12 `Single Value` gravitation rows and 48 seismic `Max/Min` rows. These `Max/Min` values are not promoted to concurrent signed PMM demands.
- Stations: **0, 2225, 4450 mm**. The separate old connectivity length is **5150 mm**. A stored `free_length_mm=4450` is a historical reported input, not a source-qualified regulatory `l_n`; physical member endpoints and releases are not resolved.
- Captured first-station raw `Grav_Ult` **M3 = −28.627450838775502 kN·m**; separate design summary reports **M3 = −171.5232 kN·m**. No accepted transformation linking the two is provided in the scoped evidence.
- 19 October archived input model identifier **165ce9b0763f...**, earlier cutset historical identifier **fc09e5eeb1e1...**, and cutset candidate EDB identifier **61fa288fe6aa...** are different identifiers. The old cutset explicitly records `authority_rebound=false`, B5/B6 absent and current result epoch NOT_QUALIFIED.
- The separate 86-column story comparison reports **194,176.996 kN** sum of design compressions vs **276,640.2736 kN** native story-bottom pressure: **82,463.2776 kN** difference, **42.4681% relative to the first sum**. These have not been validated as equivalent structural operands; no global-sway conclusion is issued.
- Global Δ / M6-B / source-verified A17–A20 materializations are **not closed** in the bounded archive. The old source has producer *code*, but this archive does not contain a qualified current 235 A17/A18/A19/A20 input chain. This is a scoped-evidence finding, not a claim about every file elsewhere.

## Reproduce offline

Run on the **original untouched** audit ZIP already available in the user's files:

```bash
python -m examples.s1g_archive_audit /path/to/TBDY_COLUMN_EXTERNAL_AUDIT_2026-10-20.zip
COLUMN_S1G_SOURCE_ZIP=/path/to/TBDY_COLUMN_EXTERNAL_AUDIT_2026-10-20.zip python -m unittest discover -s tests -v
```

Any changed source byte, missing file, altered census or incompatible source/status field triggers fail-closed. Current GitHub CI runs ledger and negative tests and **skips** the full original ZIP test unless the archive is supplied; this distinction must remain explicit.

The audited local downloadable bundle includes the 3 exact original JSON files, a stand-alone reader and eight tests executed against the real archival 60-row source. Keep it separate from current-model data. No ETABS live action was performed.

## Next evidence dependency

A real product-positive path needs: current EDB and analysis-generation identity; B5/B6 complete population; source-qualified physical I/J and connectivity/release records, A17 story sway, A18 restraint, A19 free length/k, A20 concurrent end moments and explanation of source/design moment differences, and source-authorized M6-B second-order effects. No synthetic `READY` flags or archived path equality can substitute for those facts.

**Status:** `ARCHIVE_CHECKED_REAL_COLUMN_DESIGN_BLOCKED`. This is progress in historical source reconciliation, **not** a column 235 PMM design PASS.
