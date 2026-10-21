# S1-C — all-station PMM / factual handoff

**Ref:** feridunfc/Column, October 21, 2026. Codespaces only; LIVE ETABS HOLD.

## Implemented
- Explicit per-case, per-element physical station identity and independently specified **expected** case/station census.
- No silent filtering of interior stations. Selected numerical PMM candidate reports actual governing state, station and element.
- Reuses the same accepted source mathematics: `physics/rebar_layout.py`, `physics/rebar_selection.py` and `physics/section_capacity.py`. It does not recalculate capacity in the UI or report.
- Source/generation/case, mixed steps, missing stations, wrong elements, duplicate stations, extra stations and modal/max/min negative tests.
- The old B5 factual contract is preserved by the prior `recorded_etabs.py`; `station_compiler.py` stages its output as **RAW_FIRST_ORDER / RECORDED_ETABS**. It never makes COM calls.
- The three exact historical Grav_Ult stations in fixture remain 0/2225/4450 mm, not a verified current B-BLOK design scope.

## Deliberate blockers — do not bypass
1. Existing fixture contains only 3 Grav_Ult factual rows, not all 60 archived rows and not all required design combinations/stations. `expected_station_keys` is an independently supplied expectation; it is **not** a guarantee of model-wide completeness.
2. The compiled ETABS factual demands are **not the final N–M2–M3 demands**. Minimum eccentricity, global/member second-order effects, signed/seismic combination semantics, modal M6-B, and source/epoch/current-generation validation remain unqualified.
3. `FINAL_DESIGN_REVIEWED` and arbitrary `basis_refs` cannot upgrade `RECORDED_ETABS` to PMM PASS; the S1 evaluator now explicitly blocks it. Numeric PMM remains limited to the `SYNTHETIC_VALIDATION` path until a verified final-demand producer exists.
4. Legacy S1-A I/J-only synthetic fixtures retain backward compatibility, but explicit station demands **require** an expected-station census.
5. The supported station key contains output case, element ID, member station and element station. Multi-step/dynamic histories and frame-end topology equivalence are not qualified; conflicting rows are rejected.

## Next concrete implementation: S1-D
Carry forward a verified, model-wide **expected** case/station population from the existing ETABS B5 provider; source fingerprint/epoch/current generation; documented load-combination classification; first/second-order/minimum-eccentricity production with independent numeric oracles. Only after this can `RECORDED_ETABS` enter the actual PMM candidate selection path.

This report marks source-bound **code correctness under the tested fixture scope**, not an approved engineering design.
