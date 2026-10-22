# Supervisor / Worker — Clean Column Core, Sprint S0→S1

> **Historical task — not the active Supervisor instruction.** Start with [AGENTS.md](AGENTS.md), then read the full [current constitution](docs/architecture/COLUMN_CONSTITUTION.md) and [Supervisor task](docs/tasks/COLUMN_SUPERVISOR.md). This historical prompt does not authorize work beyond the current A/B scope.

**Mission:** Complete first recorded-ETABS static column N–M2–M3 / selected rebar / PMM result without creating a competing full engine, another COM transport, or a generic process framework.

## Sources
- Prior reference: local source snapshot metadata b43b2e249b20ec9d3efd49d159aab867fb5a7d06; tree 324981f87b27030505944707d83bbb6097217a38. This snapshot is NOT known to be an accessible remote branch.
- New repository: this clean `feridunfc/Column` project. Never overwrite the running Windows COLUMN_PRODUCT.
- Live ETABS `RunAnalysis`, `StartDesign`, setter, scratch mutation, install, deploy: **HOLD** pending explicit operator approval.

## S1 deliverables
1. Extend immutable contracts for QualifiedProjectSnapshot, QualifiedDemandState, ProjectBasis, ColumnGeometryFacts, SelectedLongitudinalCage and CheckResult. Keep source/epoch/case/axis/units exact.
2. Write one offline recorded-fixture producer that derives material and section, demand N–M2–M3, load scope and design context. Do not infer dimensions from section names or require manually assembled `reviewed_*` context in success tests.
3. Inspect and independently test the existing `section_capacity`, `rebar_layout`, and `rebar_selection` kernels. Select one physics owner per quantity, not duplicate live formulas.
4. Connect **source-qualified facts → deterministic selected longitudinal layout → biaxial PMM result → single typed JSON/HTML outcome**. An insufficient column is a calculated FAIL, not software failure.
5. Prove adequate and inadequate numerics, changed column ID, axis/sign reversal, case mismatch, epoch mismatch, missing data, and no two engines.
6. Report test commands / actual pass-fail numbers and source identity, not an unsupported release claim.

## Parallel offline native track
Fake-COM tests for immediate return, delayed return after wait timeout, no return, failure during restore and double admission. Record `RUNNING_UNCONFIRMED` instead of pretending `Future.cancel()` stops native COM.

## Definition of Done
- Product-path tests generate real inputs themselves, no artificial `reviewed_*` injection.
- Independent math oracle outputs expected values and engineering tolerances.
- One qualified N–M2–M3 state per demand; one report artifact; no live ETABS.
- Source/version/CI results recorded, with supported scope clearly marked.
