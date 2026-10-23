# COLUMN C8 — SUPERVISOR BATCH HANDOFF (worker candidate)

**STATUS: HANDOFF_PREPARED_UNTESTED — NO SUPERVISOR REVIEW HAS OCCURRED.**

Owner instruction of 2026-10-23: implement through C8 in order, **defer test execution**, present Supervisor only at final stage and decide merge later. This file is the **worker-prepared input for a future independent Supervisor**, NOT a Supervisor patch, PASS, ACCEPTED_AB, release approval or merged commit.

## 1. Fixed source and branches

- Repository: `feridunfc/Column`
- Protected main after owner-directed B development merge: `9269a00f5f5471ab68413c039912cafb2cf4db39` (unchanged by these C drafts).
- C2 tested candidate parent: `worker/v132-c2-scenario-geometry-20261023@e560b825003b44855f3b19091f90c106d06ccc92`, tree `1abda87cf2944c7aa951b7d0686d8fd59f700c11`.
- C3–C8 candidate branch: `worker/v132-c3-c8-column-candidate-20261023`. C8 HEAD/tree obtained from exact branch ref when requesting final review.
- Canonical documents: `COLUMN_CONSTITUTION.md`, `COLUMN_WORKER_AB.md`, `COLUMN_SUPERVISOR.md`, `AGENTS.md` **byte-preserved**; v1.3.1 remains binding.
- Legacy original selected physics `physics/section_capacity.py` and `tests/independent/oracle.py` byte-preserved. No native ETABS, live analysis or model mutation.

## 2. Sprint commit chain — independently inspect each diff

| Slice | Implementation commit | Claim |
|---|---|---|
| C0 | `c3cf84fb39d6928b7bb069683945e0fa53f13787` | C0 physical column source branch |
| C1 | `7bb5f92fd47e048a4446e6e749b2531fdb3c4cfc` | C1 source-qualified first order; 85 test GitHub CI before deferral |
| C2 | `e560b825003b44855f3b19091f90c106d06ccc92` | C2 geometry and immutable trial; 95 test prior baseline |
| C3 | `46c4ff91ac648a26c6375ca3330f3d4b0a3eff67` | EI/stability input and method census, not approved |
| C4 | `d98dbdc780e2a8c796ca4697900e549d21e4976f` | Explicit signed demand and second-order branch mapping |
| C5 | `4e6da09fb20ded6d19f824d4ba63963e21149b95` | Candidate check coverage and fail-closed evaluator |
| C6 | `26240018a55ad3d9f3c099658bf69b76b21e1fe1` | Public check_column and one immutable JSON/HTML result |
| C7.1 | `50bb11a4aa3853a0d665e7e98b9cc87f9d6babf3` | Frame-matched B-section numeric-only diagnostic |
| C7 | `d0390ba3c105d4c6fa17645c999e031537b762ad` | 9 candidate integration/negative tests and C01-32 matrix |
| C8 | exact HEAD is branch tip after handoff-file commit | single frozen candidate review package; **not tested/accepted** |

**Diff scope:** `git diff e560b825003b44855f3b19091f90c106d06ccc92..HEAD` (C3–C8) and `git diff 9269a00f5f5471ab68413c039912cafb2cf4db39..HEAD` (cumulative C0–C8).

## 3. Implementation actually present

- C0/C1/C2: already tested source draft and immutable physical cage/selected target/scenario; verified first-order signed source mapping, declared geometry only.
- C3: separate declared EI2/EI3, local/global P-Delta branch records, per-direction complete story population; **no** unverified EI or length factor selected as normative and **no** numeric second order computed.
- C4: preserves C1 source metadata, explicit parent response, case/step/station and derived effect branch census; transformed source effects are **unapproved** and not blindly added.
- C5: `ColumnEvaluator` takes explicit `MemberDemandOutcome`, retains all externally required check coverage. Where C1 frame/evidence is known it invokes actual B `SectionSolver` for a sampled **numerical observation** only. No code PMM PASS, second-order, shear, confinement or joint approval.
- C6: `check_column(CheckRequest)` composes the above on one immutable selected target, returns `ColumnResult` and strict JSON/escaped HTML from the **same result**; `INCOMPLETE_NOT_CODE_APPROVED` only. No `design_column` search.
- C7: 9 new independent analytic/negative end-to-end test candidates and C-01…C-32 independent evidence matrix, **unexecuted by user request**.
- C8: this handoff, open findings and exact-HEAD reviewer runbook; **no independent decision**.

## 4. OPEN safety and governance findings

| ID | Severity | Required closure evidence |
|---|---|---|
| B9-F02 | BLOCKING | Global axial-root admissibility / discontinuity, tangent and multiple roots; independent numerical source verification |
| B9-F03 | BLOCKING | 72→144 observed delta 15,301.269782 Nmm > 1,000 Nmm; 288 has 4 missing roots. Independent acceptable angular error bound |
| C02-SCOPE | BLOCKING | v1.3.1 C-03/AGENTS do not authorize C release; owner-ratified C-02 versioned amendment, three canonical docs and locks updated together |
| C3-EI | OPEN | Accepted source/method for EI and effective length, story whole-population verification and local/global second order |
| C4-ACTIONS | OPEN | Independently qualified source for second-order/mode/combination branches, complete response population |
| C5-CODE | OPEN | Independent TS500/TBDY normative rule cards/acceptance and B numeric quality; no false observed utilization → PASS |
| C6-SCOPE | OPEN | D shear/confinement and E story/joints not implemented; do not claim complete code check |
| C7-TESTS | DEFERRED | Owner-requested final validation suite not yet executed, independent Supervisor still pending |

## 5. Final-stage test/review runbook — NOT RUN NOW

Start from exact candidate HEAD in a clean *observed* working tree (do not reset unknown user work):
```bash
git fetch origin
git switch worker/v132-c3-c8-column-candidate-20261023
git status --short --branch
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
python tools/check_architecture_contract.py
python -B -m unittest discover -s tests -v
python -m examples.section_pilot
```

Then independently:
1. Confirm source doc hashes, locked kernel/oracle signatures, six-component r×F and distinct physical-end mappings.
2. Run C7 analytic 1,000 N × 100 mm = 100,000 Nmm against independent hand calculation; do not copy expected values from the implementation.
3. Falsify C3 duplicate axes, invalid story population, wrong runs; C4 modal/envelope/step recombination; C5/C6 incomplete scopes, forged PASS and stale selected candidate.
4. Review B9-F02/F03 remaining numerics **without** raising tolerances, deleting tests or suppressing unresolved outcomes.
5. Review TS500/TBDY primary source rule references before allowing any normative member outcome; check D/E future scope and open C-02 change control.
6. Independently disposition each C-01…C-32 clause and each C0–C8 sprint: `ACCEPTED`, `CHANGES_REQUIRED` or `BLOCKED`, with finding IDs / regression reruns.
7. Only *after* gate closure decide whether C integration PR can be merged to main. No auto merge or production-ready claim in this handoff.

**C8 is the end of candidate authoring, NOT the test/acceptance phase.**
