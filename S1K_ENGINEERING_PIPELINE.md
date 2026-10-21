# S1-K — Pure column numeric pipeline and clean forensic boundary

## Architecture

- **Production-direction math core:** \`tbdy_column_core\` remains general-purpose and uses N, mm, Nmm, MPa. New entry point: \`tbdy_column_core.s1_pipeline.run_s1_numeric_preview\`.
- **Historical incident tooling:** \`tools/legacy_audit/s1f_gateway.py\`, \`s1g_archive.py\`, \`s1h_recovery.py\`. These carry B-BLOK/Column-235-specific data, archival dates, pinning and replay assertions. They are **excluded** from the distributed \`tbdy_column_core\` package. Existing examples and tests import the tools explicitly; nothing in the core imports them.
- **No native ETABS**, COM, gateway ownership changes, automatic provenance rebind, or final design PASS.

## Full-chain synthetic-only numerical experiment

\`\`\`
Raw S1ColumnSnapshot (unique signed static case × element × station)
     → S1-E two-axis A18/A19/A20 synthetic effective-length and slenderness basis
     → S1-D minimum eccentricity branches and second-order arithmetic
     → ColumnDemandState derived branches (duplicates physical station are permitted)
     → pure rebar layout and PMM candidate trial
     → S1NumericTrial (not an engineering design release)
\`\`\`

The S1ColumnSnapshot raw census is NEVER reused as a container for branched demands. S1-D may produce several ± minimum eccentricity branches at the same raw station. The pipeline verifies that each expected input station is retained, no new station is introduced, and output case/state identities remain distinct before PMM evaluation. Real RECORDED_ETABS remains blocked; no human-readable review label can override that.

### %5 axial-force issue

Former S1-E code rejected any synthetic signed static I/J axial force difference >5%, an arbitrary tolerance not established as a code limit. It is removed: first-order signed end forces may differ due to gravity/body forces. S1-E already uses the individual \`nd_compression_n\` for every demand state when constructing magnification bases. This removal is **not** an authorization to average I/J Nd for member stability or to extrapolate a story sum: those are separate, still unqualified calculations.

### Explicit unresolved engineering gaps

The numeric trial is **NOT** TS500/TBDY-approved. In particular, the following issues still require independent standard review before promoting to real engineering:

- Whether minimum eccentricity must be applied to internal member sections in each design situation; existing S1-D applies the floor to ends only.
- How member-wide maximum end moment and magnification factors should be reconciled with individual station moments, and whether all local states adequately envelope moment demand.
- Two-axis sway story sums, governing compression for critical load, modal combination/provenance and analysis generation.
- All S2 scope: shear, confinement, strong-column/weak-beam, joint/short column checks.

The resulting \`S1NumericTrial.full_ts500_tbdy_design_pass\` and \`final_design_demand_proven\` are always \`False\`.

### Verify

\`\`\`bash
python -m unittest discover -s tests -v
python -m unittest tests.test_s1k_pipeline -v
\`\`\`

Original archival ZIP tests still use \`COLUMN_S1G_SOURCE_ZIP\` and \`COLUMN_S1H_SOURCE_ZIP\` environment variables. They remain optional/skip in ordinary CI and do not belong to structural engineering physics.

## Follow-up engineering sprint

Research and independently check TS500 minimum eccentricity, Eq 7.26 and 7.29/Cm station/member rules, and formalize per-station demand and per-member stability force selection. Only then introduce an explicitly qualified final-demand compiler for real ETABS or start S2 numerical kernels.
