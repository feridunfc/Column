# B8 — A/B closure candidate and blocking evidence ledger

**Code anchor:** B7 `ce75e58f7c07f37df02e39ac0cff9b2f6bae2f35`
**Canonical constitution:** v1.3.1
**Release:** HOLD. No self-granted G0/G1/G2.

All **32 C clauses** and **18 AB checks** have an individually indexed
worker-evidence record in `evidence/ab_closure_ledger.json`.
`SATISFIED` means a bounded worker *candidate implementation claim*,
not an accepted Supervisor finding. `UNVERIFIED` is not PASS.
`PRESERVED_DEFERRED` is lawful only where C-31 explicitly defers the
member/ETABS/design scope. This ledger is machine-checkable for coverage,
existing source references and release HOLD; those checks **do not**
prove the engineering claims.

Open blocking issues:
- FND-B8-01: C-02 procedural change remains unratified and the distinct
  independent Supervisor decision required by C-32 has not occurred.
- FND-B8-02: C-20 sampled sign-crossing evidence cannot prove globally
  unique roots; observed 72/144/288 angle stability and the oracle's
  3% agreement cannot prove a continuous-envelope numerical error
  boundary. Separate acceptability disposition needed.
- FND-B8-03: Source four-dimension semantics, scoped qualification and
  evidence authenticity need a code+fixture-specific independent audit.

**Explicitly unsupported:** full column code PASS, shear, confinement,
stability, SCWB, ETABS/COM, designer, project model, native mutation.
The pinned source physics and independent test-only oracle remain
untouched. No main merge. Local PyCharm tests are deferred by user
request; GitHub CI is a technical development signal only.

To check evidence shape:
```powershell
python tools/validate_b8_ledger.py
python tools/check_architecture_contract.py
python -B -m unittest discover -s tests -v
```

The B9 deliverable will describe independent-review instructions and a
fail-closed actual disposition. **B8 does not claim independent review.**
