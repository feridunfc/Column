# Column v1.3.1 — compulsory agent entry

Before any change, read the **entire** root files:
1. `COLUMN_CONSTITUTION.md`
2. `COLUMN_WORKER_AB.md`
3. `COLUMN_SUPERVISOR.md`

Verify v1.3.1 release and cross SHA-256 links with
`python tools/check_architecture_contract.py`.
Do not trust summaries, the old `AGENTS.md` on legacy branches, or stale PRs.
Carry forward the constitution C-01…C-32, Worker A0/A/B task and Supervisor
G0/G1/G2; a green hash check does not itself constitute engineering authority.

**Current authorized work:** A0, A and (only after separately accepted G1) B.
No ETABS COM, analysis run, member/column check, rebar search, joint/story,
DB, premature design PASS or unconditional merge. Preserve three documents
exactly; do not update lock hashes to silence a failing check. Any constitution
change requires C-02 change-control by user.

Start each task by recording role, task/release, actual branch/HEAD/tree,
source revisions, user-worktree status, three document hashes, full-reading
declaration, scope, and test/tolerance strategy. Never discard unknown local
changes. Worker cannot independently accept its own G1/G2 work.
