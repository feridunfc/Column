# B6 — Unsigned numerical result-integrity receipt

**2026-10-22 / feridunfc/Column**
**Base:** B5 `a8e623beafc9362af991aab9a67e059a14d3d19e`
**Worker:** `worker/v131-b6-result-integrity-20261022`
**Authority:** DRAFT development only. G0/G1/G2 and versioned C-02
process amendment remain unapproved; main stays unchanged.

## Motivation

B5 SHA-256 binds **declared inputs** but cannot distinguish
two outputs with different N/M states, root residuals, angle coverage,
issues or policies for the same input. B6 adds a separate, optional
**unsigned result-payload integrity record**.

## Implemented

- `section_report_bundle_json(result)` returns a stable JSON object
  `{payload,receipt}`. Payload is exactly the original
  `section_payload(result)` projection used by existing JSON and HTML;
  the original `section_report_json(result)` signature and output
  remain compatible.
- Receipt schema `column.section.result-receipt.sha256.v1` includes:
  `payload_sha256` of canonical UTF-8 sorted compact JSON payload;
  separate `input_sha256` copied from B5's input fingerprint;
  payload schema and explicit **unsigned** interpretation.
- Passive HTML prints the same receipt as the JSON bundle using
  the already-produced result payload; no source input fingerprint
  recomputation and no engineering recalculation.
- `verify_section_bundle_json` returns typed local verdict:
  MATCH / MISMATCH / MALFORMED / UNSUPPORTED, with issue codes.
  It independently re-encodes the received JSON payload to check
  payload digest and input-link digest. JSON duplicate keys, nonfinite
  values, malformed structures and unknown receipt versions fail closed.
- Nine new tests prove deterministic JSON/HTML binding, independent
  SHA-256 reference computation, altered N, issues, status, missing
  angle coverage, policy, input-reference tampering, duplicate keys,
  NaN/Infinity, unknown schema and incomplete/undefined outcomes.
  A negative test explicitly shows how a dishonest party can modify
  **both** payload and checksum while retaining local MATCH.

## Semantics and threat limits

**MATCH is not ACCEPTED, AUTHENTICATED, CALCULATED, VERIFIED_TS500,
TBDY_COMPLIANT or ENGINEERING_PASS.** This is merely unsigned
integrity of the *supplied* payload against the *supplied* checksum.
Anyone can regenerate the hash; authenticating a purported original
needs an out-of-band trusted record or digital signature, **not
supplied in this sprint**. The receipt does not confirm ETABS data,
governing material sources, N-root uniqueness, numerical convergence,
engine execution, or that all necessary column-code checks exist.

The pinned legacy TS500 kernel and test-only oracle remain unmodified.
No native API, file signing, cryptographic secret management,
persistent datastore, new code compliance rule or main merge.

## Reproduction (optional local later)

```powershell
python tools/check_architecture_contract.py
python -B -m unittest discover -s tests -v
python -B -m examples.section_pilot
```

Code and CI evidence must be attached at the exact eventual B6 HEAD.
Independent engineering sign-off is a separate future Supervisor
action, not inferred from passing automated tests.
