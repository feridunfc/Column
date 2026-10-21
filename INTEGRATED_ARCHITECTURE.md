# TBDY Column — Integrated Architecture

**Date:** 2026-10-21. **ETABS live HOLD.** This is an architecture and offline calculation seed, not full column design certification.

## Architectural decision

Start with **one product contract and one public calculation path**, rather than copying existing giant application orchestrators. Import individual already-verified mathematical kernels from the old TBDY repository **only after independent numerical acceptance**. No arbitrary eight-file cap.

```text
ETABS Windows (operator-authorized only)
    → existing gateway / single COM STA / safe scratch lifecycle
    → qualified raw facts adapter: units + source identity + epoch + case + generation
    → QualifiedProjectSnapshot + ProjectBasis
    → execute_project [future public entrypoint; not yet implemented]
       → Pass 1: full story population, story sway, member EI/Nk
       → Pass 2: qualified member demand, minimum eccentricity,
                  second-order, longitudinal rebar, PMM,
                  design shear, transverse cage and detailing
    → ONE typed ProjectResult + coverage ledger
    → passive JSON / HTML / PDF
```

**Only** `execute_first_pass()` and the qualified signed linear-static TS 500 Eq. 7.13 nonsway gate are presently implemented in this repository.

## Ground rules

- Internal units **N, mm, Nmm, MPa**; user presentation **kN, cm, kN·m, MPa**.
- Immutable provenance: model fingerprint, evidence epoch, analysis generation, signed case/state, member and story identity. No mixing generations or modal envelope values with simultaneous signed results.
- TS 500 Eq. 7.13: `phi = (1.5 Δ_i / V_fi) * Σ(N_di / l_i)`; individual member lengths `l_i` matter. A number above 0.05 does **not** by itself justify importing a 0.25 REANALYSIS threshold.
- Modal M6-B engineering semantics unresolved; reject unsupported response-spectrum combinations rather than calling static or setting net vertical earthquake effects to zero.
- **Section geometry**, **proposed longitudinal bars** and **final transverse cage** are separate typed objects.
- Only one selected PMM / shear / second-order physical value per qualified state; reporting must never calculate competing engineering values.
- A `SHA256` report digest is a fingerprint, not a regulatory approval.
- Existing ETABS gateway lifecycle should be retained, *not* a new Python COM stack; a worker timeout does not prove COM cancellation.
- Full 260-column acceptance must be measured by real required control coverage; an infrastructure identity PASS is not structural capacity PASS.

## Migration decision table

| Prior TBDY function family | Decision |
|---|---|
| design/columns/moment_magnification.py | reuse AFTER independent numeric oracle |
| design/columns/section_capacity.py | reuse AFTER independent numeric oracle |
| design/columns/rebar_layout.py, rebar_selection.py | reuse AFTER independent numeric oracle |
| column_a22_moment_magnification.py | extract narrowly; no giant application copy |
| column_p7_runtime.py, column_vc_runtime.py, column_final_cage.py | producer/evaluator separation |
| coverage/column_denominator.py | reuse narrow, with complete source census |
| packages/etabs_gateway | KEEP external native/STA owner |
| column_live_process.py, column_live_workspace.py | repair lifecycle and connect via adapter |
| product_reports/column_live_report.py | passive projection of the ONE typed result |

## Delivery slices

- **S0**: qualified source contracts + signed static Eq. 7.13 gate + negative tests (this repository).
- **S1**: recorded actual ETABS column facts → generated demands → deterministic longitudinal rebar → checked biaxial PMM → same JSON/HTML report.
- **S2**: design shear both axes → Vc/Vr → geometrically real selected ties/crossties and confinement.
- **S3**: complete story second-order path including independently accepted modal method; feed actual amplified demands into PMM and shear, exclude double magnification.
- **S4**: offline fake COM job lifecycle first; later separately operator-authorized Windows live run, late return and source restoration.
- **S5**: all 260 columns and every supported control via the same qualified result/coverage ledger.

Bindirme/kenetlenme is outside this first release scope; explicitly mark missing checks, never claim full-building TBDY compliance.

## Closure rule

A sprint closes only for **real public entrypoint → automatically produced inputs → accepted physics owner → typed output → passive report → independent numerical oracle**. Unit-test counts or new dataclasses alone are not completion.
