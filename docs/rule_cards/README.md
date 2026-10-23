# Column Rule Cards — engineering catalogue (draft)

**Status:** DESIGN-ONLY / NOT RATIFIED / NOT CONNECTED TO A PUBLIC CHECK API  
**Constitution:** `COLUMN-OOP-CONSTITUTION 1.3.1`  
**Base:** `main@9269a00f5f5471ab68413c039912cafb2cf4db39`

This catalogue is a structured engineering specification for future checks. It does **not** authorize `check_column`, does not change the v1.3.1 A0/A/B scope, and does not turn the existing section-capacity pilot into TS500/TBDY code compliance. No card in this draft may emit an engineering `OK` until its normative source, applicability, formula implementation and independent verification are accepted.

## Why a rule card, not just an enum?

A comparison direction (`DEMAND_OVER_CAPACITY`, `PROVIDED_OVER_REQUIRED`, `CONDITION`) is only the last step. A usable card also specifies:

- exact code edition/clause/equation and source identity;
- applicability and load-case/evidence prerequisites;
- typed input quantities and canonical units (N, mm, Nmm, MPa);
- equations, sign conventions, section/material parameters and governing combinations;
- decision direction and threshold derivation;
- missing/ambiguous/unsupported-data behavior;
- expected engineering evidence, independent tests and failure action;
- implementation and normative-validation state.

## Status model

- `OK`: the rule is applicable, its authoritative inputs and method are qualified, calculation completed, and the specified criterion is satisfied. It is not a whole-column/global design PASS.
- `WARNING`: an observation or warning threshold was reached; this is not a passing result.
- `FAIL`: a qualified, applicable normative rule was evaluated and violated.
- `NO_DATA`: a required input or source receipt is absent.
- `UNRESOLVED`: conflicting evidence, ambiguous method, or numerical root/convergence is unresolved.
- `NOT_EVALUATED`: no accepted implementation or normative method is available.
- `NOT_APPLICABLE`: applicability was explicitly resolved and evidenced.

Keep **status** (engineering result) separate from **level** (INFO/WARNING/ERROR/BLOCKER). Missing data must never become zero; an unimplemented check must never become OK; an observed utilization above 1 must be surfaced even when the normative rule is not yet accepted.

## Direction semantics

| Direction | Metric | Pass comparison |
|---|---|---|
| `DEMAND_OVER_CAPACITY` | (u = D/R), with (R>0) | (u \le 1) |
| `PROVIDED_OVER_REQUIRED` | (r = A_{provided}/A_{required}), with (A_{required}>0) | (r \ge 1) |
| `CONDITION` | explicitly defined predicate | true |
| `INTERVAL` | measured scalar | (x_{min} \le x \le x_{max}) |
| `MAXIMUM` | measured scalar | (x \le x_{max}) |
| `MINIMUM` | measured scalar | (x \ge x_{min}) |

Do not apply a scalar ratio to biaxial interaction unless the card defines the load path and the resistance-surface intersection. Do not compare values with incompatible units.

## Source handling

- The primary TBDY reference is AFAD's published 2018 PDF: https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf
- TS 500 equation references in this draft were cross-read against an accessible copy of TS 500/February 2000: https://www.yuzyilyapidenetim.com.tr/documents/TS500.pdf . This copy is a discovery aid, **not proof of licensed/official edition status**. Before an executable release, pin the authorized applicable TS 500 edition and record a local clause/equation review receipt.
- Secondary technical pages are not treated as authority for a production rule.
- Any clause/equation revision requires a new card revision and regression evidence. Never silently edit a threshold to make a test pass.

## Catalogue index

See `catalog.yaml` and the individual cards:

- `RC-GEO-001`: section dimensions and axial-force area prerequisite.
- `RC-REBAR-LONG-001`: longitudinal bar diameter and reinforcement ratio.
- `RC-BAR-PLACEMENT-001`: cover, bar containment and collision geometry (geometric validity only).
- `RC-PMM-001`: axial force + biaxial bending interaction; intentionally non-executable pending a validated resistance surface.
- `RC-SHEAR-TS500-001`: base TS 500 shear resistance equations, with seismic-column exclusions.
- `RC-SHEAR-TBDY-COLUMN-001`: TBDY 7.3.7 column capacity shear and upper bound.
- `RC-CONFINEMENT-TBDY-COLUMN-001`: TBDY 7.3.4.1 end confinement and transverse reinforcement.
- `RC-SECOND-ORDER-001`: member stability / second-order effects; requirements enumerated, equations intentionally unresolved.

## Gate to implementation

1. Independent engineer verifies the exact normative edition, clause text, equation transcription, units and branches.
2. Each card receives source review evidence, not merely a URL.
3. Each formula receives hand-calculated boundary examples and independent oracle comparisons.
4. The runtime adapter consumes a typed immutable `CheckRequest` and returns a `CheckResult` containing rule revision, inputs/evidence, formula trace, measured value, limit, utilization, status and issue codes.
5. A future `check_column` API remains blocked until the owner ratifies C-02 and updates the canonical constitution package and hashes together.

## Future typed result contract (not implemented in this branch)

```python
class PassRule(Enum):
    DEMAND_OVER_CAPACITY = "demand/capacity <= 1"
    PROVIDED_OVER_REQUIRED = "provided/required >= 1"
    CONDITION = "predicate is true"
    INTERVAL = "lower <= value <= upper"
    MAXIMUM = "value <= limit"
    MINIMUM = "value >= limit"

class Status(Enum):
    OK = "OK"
    WARNING = "WARNING"
    FAIL = "FAIL"
    NO_DATA = "NO_DATA"
    UNRESOLVED = "UNRESOLVED"
    NOT_EVALUATED = "NOT_EVALUATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"

@dataclass(frozen=True)
class CheckResult:
    rule_id: str
    rule_revision: int
    direction: PassRule
    status: Status
    level: str                 # INFO / WARNING / ERROR / BLOCKER
    metric: float | bool | None
    unit: str | None
    limit: float | None
    utilization: float | None
    input_evidence_refs: tuple[str, ...]
    formula_trace: tuple[str, ...]
    issue_codes: tuple[str, ...]
```

A future `shear_check(demand, section, rule_revision, evidence)` must first resolve the applicable card and code branch, then calculate. It must return `NO_DATA` for absent qualified demand/material/detailing data, `UNRESOLVED` for contradictory or unqualified method evidence, `NOT_EVALUATED` while the card is not implemented/accepted, and `FAIL` only for a verified applicable rule violation. A boolean `has_failures` is not a substitute for exposing an observed utilization above unity.
