# C SERİSİ — Supervisor toplu teslim indeks dosyası

**Durum:** PENDING; burada Supervisor kabul beyanı bulunmaz.

Toplu patch dosyaları sürüm ve SHA bazında buraya eklenecek. İçerik:
1. `COLUMN_CONSTITUTION.md`, Worker ve Supervisor hash/sürüm kanıtı ve `AGENTS.md`; C-02 CR onayı veya açık sapma.
2. `main` tabanı + tüm C0-C7 committed HEAD/TREE/parent ve reviewable diff (sprint log).
3. Her sprintin source-backed normatif kural kartı, ilk/son test komutları, CI run, oracle numerikleri, exception/Unsupported/Missing matrisleri.
4. C-01…C-32 madde bazlı kapsam/kanıt ve B9-F02/F03 güvenilirlik kapanışı; D/E/F/G/H ayrı kapsam.
5. Çıktı: `ACCEPTED / CHANGES_REQUIRED / BLOCKED`; gerekçeli findings, her biri clause+file+symptom+regression.
6. Patch alanı Supervisor'ın bağımsız inceleme sonucunu taşır; kod yazan Worker aynı kod için bağımsız kabul vermiş sayılmaz.

**Mevcut G0/G1/G2:** PENDING; **C0/C1:** TESTED_DRAFT; **release:** HOLD. CI başarıları, normatif kaynak onayı veya full-column PASS değildir.

## C2 implementation candidate (2026-10-23)

- `worker/v132-c2-scenario-geometry-20261023@5892f175c674ff29900ca48c61c5b60fcf2070d4`, tree `51efa895ef20a467ece4fa32a89bc54f817e0ecf`.
- [CI 39941320817](https://github.com/feridunfc/Column/actions/runs/39941320817): 4/4 PASS, 95 tests per environment.
- `DesignScenario` and single-target `TrialContext` immutable; `MemberMechanics.prepare_geometry` only declared geometry, no stiffness/second-order approval.
- C-02 v1.3.2 amendment and independent acceptance remain `PENDING`, B9-F02/F03 `OPEN`.

## C8 consolidated candidate packet

See `docs/c_series/C8_SUPERVISOR_BATCH_REVIEW.md` and `docs/c_series/OPEN_FINDINGS.md`. Current last implementation code HEAD before C8 `d0390ba3c105d4c6fa17645c999e031537b762ad`. Exact C8 HEAD/TREE is the final branch ref, not asserted until fetched. Supervisor independent review, deferred tests, full-column code acceptance and merge are **not performed**.
