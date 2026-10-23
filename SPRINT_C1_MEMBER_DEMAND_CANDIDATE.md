# C0/C1 column-entry implementation candidate — source-bound first-order demands

**Integration parent:** main `9269a00f5f5471ab68413c039912cafb2cf4db39` after owner-directed B1–B11 merge. This is an explicit, separately reviewed C candidate, **not** a release to main.

C0 physical member/cage contracts were ported from the earlier isolated C0 draft without changing the pinned section physics or canonical governance files. C1 adds `MemberDemandCompiler.compile` with:
- exact immutable physical member, candidate and section revision;
- immutable externally expected `ResponseKey`/station and source population ID census;
- single explicitly scoped `AnalysisBundle.qualify` evidence catalog with verification receipt;
- physical centerline station and face mapping independent of analysis I/J;
- six-vector source→target transformation with the declared destination frame and `r×F` transport;
- a declared axial sign convention and signed, source-coincident vectors (no envelope fabrication);
- typed READY_FIRST_ORDER_ONLY, INCOMPLETE_SOURCE, UNQUALIFIED_SOURCE, INVALID_STATION_MAPPING;
- no hidden ETABS call, second-order adjustment, shear/capacity check, code PASS, design search or native access.

Next C2 must implement `MemberMechanics.prepare_geometry`, explicit stiffness/second-order basis, and a scoped `ColumnEvaluator`; only when independently verified source qualifiers and selected TS500/TBDY rules are implemented can full `check_column` legitimately advertise actual column compliance. **B numerical quality and G0/G1/G2 are still unaccepted.**

**C-02 owner disposition:** User asked for rapid source merge and immediate Column progress on 2026-10-23. This authorizes *draft implementation* but does not itself claim the v1.3.1 contract has been formally amended. A versioned C-02 amendment and independent review remain pending before a C release/merge.
