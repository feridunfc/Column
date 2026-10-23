# C-02 ChangeRequest — provisional B repairs and early C development

**Recorded owner instruction:** On 2026-10-23, proceed to correct defects in the B series and move into C development; defer Supervisor test/control and formal acceptance review.

**Existing authority:** COLUMN_CONSTITUTION.md v1.3.1, clauses C-01/C-02/C-03/C-20/C-29/C-30/C-31/C-32; COLUMN_WORKER_AB.md §4–7 and COLUMN_SUPERVISOR.md G0/G1/G2.

## Conflict and bounded provisional interpretation

The v1.3.1 constitution requires accepted G0/G1 before B implementation, accepted G2 before A/B closure, and new explicit authority before C. The latest user instruction supplies authorization to prepare B corrections and C work, **not** evidence that G0/G1/G2 or A/B numerical acceptance already occurred.

This draft therefore treats:
- B10 and C0 as source-controlled **candidates** on separate worker branches, not merged into main;
- GitHub CI as development regression, not the postponed independent Supervisor acceptance;
- any unsatisfied B numerical root/angle requirement as a blocker to publicly claiming complete section suitability and to relying on that capacity for a Column PASS;
- C0 as strictly domain contracts until B numerical and project-evidence acceptance is resolved;
- no live ETABS, column compliance approval, native mutation, broad engine or hidden solver shortcut.

## Proposed constitutional decision (NOT YET RATIFIED)

Prepare a versioned prospective amendment v1.3.2 clarifying that isolated C implementation candidates can be developed during a single batched independent G0/G1/G2 review, while retaining final release-order gates. The amendment should update C-02 procedural change control, C-03 effective implementation boundary, C-31 stage table, C-32 staged review rules and all three canonical hash pins **together**. No formula, tolerance, section physics, oracle, technical standard requirement, or engineering acceptance condition is changed.

**Alternatives:**
1. Keep v1.3.1 unchanged: hold all C code until formal B acceptance; preserve C0 on draft branch. Safest strict reading.
2. Ratify proposed v1.3.2 to allow parallel **draft** preparation, but forbid release of check_column until formal B acceptance and C-specific acceptance. Recommended operational path given explicit user request.

**Current status:** OWNER INSTRUCTION RECORDED; FORMAL VERSIONED AMENDMENT NOT YET RATIFIED. Canonical v1.3.1 files, hash-lock tool, main and legacy remain unchanged. Neither a green CI nor this draft confers G0/G1/G2 acceptance.
