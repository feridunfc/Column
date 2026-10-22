# C-02 — User-directed batched sprint review (2026-10-22)

**Decision owner:** User, in conversation after Codespaces A validation:
"bir kaç sprint gidelim sonra supervisor incelemesi yaparız. next sprint."

**Conflict:** Constitution v1.3.1 C-32 and Worker §4 require independent
G0/G1 approval before implementing B. User now requests implementation
across multiple sprints followed by one independent Supervisor review.

**Provisional execution interpretation:** B changes are prepared on a fresh
**draft Worker branch**, with separate commits, test artifacts, and no merge
into main. No G0/G1/G2 ACCEPTED may be inferred from CI or self-audit.
Supervisor review and C-02 versioned amendment of all three canonical
documents are **still required** before formal v1.3.1-compatible acceptance.
This document is a transparent deviation record, NOT a secret change to
any canonical document or a self-issued Supervisor approval.

**Protected:** main and its three document hashes, legacy archive,
TS500 physics mathematical source and independent oracle source. No live
ETABS, model mutation, member design PASS, third-party side effects.
No candidate-generator transplantation.

**Next sprint:** supplied-cage / three-request section capacity pilot.
Numerical demonstration only; any unproved multiple-root or incomplete
envelope must be reported as numerically unresolved, not physical
OUTSIDE_AXIAL_CAPACITY.

**Disposition before integration:** independent Supervisor must decide
whether to approve a formal C-02 amendment and review all sprint diffs.
A green CI alone never authorizes merging the draft PR.
