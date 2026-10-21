# Column — TBDY Column Clean Start

An **offline-first** Python structural engineering seed. The only implemented engineering calculation is the narrowly qualified **TS 500 Eq. 7.13 story nonsway gate** for complete, signed, linear-static story states. This is **not** an approved full-column designer.

## Run in GitHub Codespaces

Open **Code → Codespaces → Create codespace on main** and run:

```bash
python -m unittest discover -s tests -v
```

Python 3.12+; no ETABS or Windows installation required for this starter.

## Architecture

- `tbdy_column_core/contracts.py`: immutable, provenance-qualified story and column facts, internal N/mm/Nmm/MPa units
- `stability.py`: TS 500 Eq. 7.13 calculation; no modal reinterpretation
- `engine.py`: pure first-pass calculation
- `report.py`: deterministic passive JSON/hash, never an engineering approval
- `tests/test_stability.py`: numeric, lineage and fail-closed regression tests
- `INTEGRATED_ARCHITECTURE.md`: product direction and limits
- `SPRINT_0_SUPERVISOR_TASK.md`: S1 bounded implementation instructions

**Important:** The original `feridunfc/TBDY` project has not been copied. Reuse of its accepted calculation kernels requires independent numerical verification. ETABS live operations remain **HOLD**. CI test success does not establish complete TBDY compliance.
