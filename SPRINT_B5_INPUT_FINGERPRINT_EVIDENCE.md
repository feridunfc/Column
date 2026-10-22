# Column B5 — Reproducible declared-input fingerprint (candidate)

**B4 baseline:** `3e1f750a82de911e5973b27c1f011fc47310d3ff`
**Worker branch:** `worker/v131-b5-input-fingerprint-20261022`
**Review:** Independent Supervisor G0/G1/G2 NOT ACCEPTED; open C-02
procedural amendment must be formally settled before engineering acceptance.

## Change and threat addressed

A section's display identity, revision and headline geometry are not a
sufficient fingerprint of the numerical calculation: physically different
supplied rebar centres, steel design laws, input evidence or root/angle
policy may reuse the exact same section revision label.

A new pure `section_input_fingerprint(problem,kernel_ref=...)` hashes
canonical serialized **declared** engineering inputs using
`SHA-256(column.section.input.sha256.v1)`. Every public
`calculate_section` result contains a typed
`CalculationInputFingerprint(schema,sha256)`. It is carried even when
the calculation is numerically unresolved, unsupported or radial direction
is undefined. Reporting exposes the unchanged result field in JSON/HTML
and never recomputes the digest.

The digest binds section/material/concrete/steel law and revisions,
actual bar identities/centres/diameters/steel references, cover/ties,
request kind/values, policy, local-to-global frame basis/origin and
reference/sign, declared source evidence and revisions, and the pinned
physics kernel source identifier. Units normalize to N/mm/Nmm/MPa/rad.
Finiteness and deterministic encoding are mandatory. An unordered
population of physical bars, steel laws and evidence refs is serialized
in canonical order; the digest preserves every value without depending
on their input list order.

## Explicit limitations

- **Not an authenticity certificate.** SHA-256 does not verify that
  a producer, material record, revision, or ETABS source is genuine.
  A caller that supplies false data gets a fingerprint of false data.
- **Not a content-addressed output proof.** Two runs with the same
  inputs but different numerical outcomes/issues share an input
  fingerprint. A separate output receipt/provenance proof would be
  needed to authenticate execution.
- **Not a physics/TS500/TBDY approval.** The source-bound TS500 kernel,
  root scanning algorithm, oracle and normative model assumptions are
  untouched. These hashes do not prove global uniqueness of the N root,
  accuracy of sampled radial envelope or full-column code compliance.
- **Not archival replay.** The digest cannot reconstruct the full input;
  source records still must be retained independently.
- **No main merge**, no native ETABS access/mutation, no unit test
  substitution for independent Supervisor gate acceptance.

## Verification
```powershell
python tools/check_architecture_contract.py
python -B -m unittest discover -s tests -v
python -B -m examples.section_pilot
```
Tests cover stable reproduction, bar/evidence reordering and mm/cm
equivalence; changed hidden geometry/steel with unchanged section
revision; policy, request, frame, evidence revision; no report recompute;
invalid typed digest and early undefined/unresolved paths.
