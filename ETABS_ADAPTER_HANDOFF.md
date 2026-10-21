# S1-B — original ETABS data reader reuse

Status: OFFLINE READ-ONLY BRIDGE IMPLEMENTED; REAL S1-B PRODUCT ACCEPTANCE OPEN.

The old ETABS COM owner is NOT copied, rewritten or executed on Codespaces. On Windows, the original verified session and gateway call the unchanged provider in feridunfc/TBDY:
- tbdy_engine.providers.etabs_column_force_result_population_provider: capture_column_force_population_expectation_from_session, capture_column_force_result_population_from_session, ColumnForceResultPopulationFact. Old main source blob SHA 3cd81e9ea7cc117ad3c6deb82e0936a4ffdcfa39.
- tbdy_engine.etabs.oapi.eq713_response_results: read_frame_force_response_from_session and Results.FrameForce ABI. Old main source blob SHA 613ce26bff3dbfb29b466453c8e2a9a44d72167.

New tbdy_column_core.recorded_etabs.import_old_b5_force_population(fact, source_unit="kN_cm_kNm") consumes the exact typed old provider's .rows, rather than its .as_dict() metadata projection (which omits rows). This function does NO COM/OAPI operations and cannot assign evidence epoch, analysis generation or final design authority.

All captured columns, output stations, signed forces, step semantics and result identities are retained. P native (compression negative in this specifically recorded convention) becomes N compression-positive. Old display units kN, cm, kN.m are mapped to N, mm, Nmm. Other units are rejected pending a documented native capture contract. Native LinRespSpec Max/Min rows are quarantined as non-simultaneous. A LinStatic single-value row is a factual result, not proof of full design combination, minimum eccentricity or second-order completion.

## Historical Column 235

The supplied local b43b2e2 archive contains docs/Column_235_Recorded_Inputs_2026-10-19.json with 60 raw Results.FrameForce rows: 12 single-value rows and 48 Max/Min rows, across three stations (0, 222.5 and 445 cm). This is not a qualified current project result.

The new repository tracks only the exact three old Grav_Ult rows as tests/fixtures/column235_grav_ult_historical_subset.json. It is deliberately labeled a SUBSET. The source hash there identifies the historical parent record but is not an authentication of a current ETABS analysis.

At first station the historical native P was -4398.029755 kN; the core's N is +4,398,029.755 N. Raw M2=+17.417664 kN.m, M3=-28.627451 kN.m. A separately displayed ETABS design flexural M3 may differ (e.g. -171.5232 kN.m); do not quietly substitute or treat them as the same demand semantics. Midspan station is 2225 mm; the existing S1 I/J-only consumer must not silently discard it.

## What remains

1. Fresh model file/in-memory model / epoch / B5 analysis generation and full model, case, step, station, beam/column population lineage.
2. Trustworthy complete design demand compiler verifying min eccentricity, correct load combination scope, member and global second order, response spectrum semantics.
3. Extend S1 assessment from only I/J ends to EVERY required qualified force station. Integrate S1B data into this compiler only with validated identity and quantities.
4. Acceptance on second real column and complete applicable model controls; independent engineering result PASS/FAIL separately from factual-record PASS.

The original COM reader remains the native owner on authorized Windows only. Live ETABS action, installer, analysis and design are HOLD. CI proves only read-only parsing/consumption and fail-closed boundaries.
