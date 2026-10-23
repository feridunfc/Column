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
