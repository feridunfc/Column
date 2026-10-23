# CR-C-02-C-20261023 — C geliştirme ve toplu Supervisor inceleme sırası

**Durum: OWNER DIRECTIVE RECORDED / VERSIONED CHANGE NOT RATIFIED.**
**Sürüm kaynağı:** v1.3.1 C-01, C-02, C-03, C-21…C-32, `AGENTS.md`, `COLUMN_WORKER_AB.md`, `COLUMN_SUPERVISOR.md`.
**Kullanıcı yönü (2026-10-23):** C'ye geç, son toplu patch'i Supervisor verecek, anayasaya sadık kal, her sprintin yaptığı işi kayıt altına al.

## Çelişki

- C-03 ve AGENTS hâlâ sadece A0/A/B aktif der. C-31 C'yi sonraki `check_column` hedefi olarak tanımlar; eski sürüm C aktif değildir.
- G0/G1/G2 ve `ACCEPTED_AB` kaydı **yok**; B11 dört ortamda unittest PASS olsa da B9-F02 ve B9-F03 sayısal bulguları açık.
- 2026-10-23 sahibin açık merge talebi doğrultusunda **B1–B11 geliştirme hattı** PR #24 ile `main@9269a00f5f5471ab68413c039912cafb2cf4db39` üzerinde birleştirildi. Bu kaynak entegrasyonu **mühendislik release değil**.
- C0/C1 şimdilik `worker/v132-c1-member-demand-20261023` içinde 85 test/ortam PASS alan bir adaydır; sahip onayı bekleyen bölüm değişikliği değildir.

## Tek seferlik sürüm önerisi — v1.3.2 (ÖNERİ, uygulanmadı)

1. C-02: Owner talimatının kapsam/defer-review kaydı; geliştirme adayları CI ile ilerleyebilir fakat test=Supervizor kabul değildir.
2. C-03: C saf offline hazırlık ve `check_column` kapsamını **taslak** olarak aktifleştir; D/E/F/G/H'yi aktif sayma.
3. C-31: C0…C8 ara sprintlerinin C iş paketini tamamlamak için nasıl ayrılacağını açıkla; D/E/F/G/H tarihini/otoritesini koru.
4. C-32: G0/G1/G2'nin nihai bağımsız kabul şartını silmeden yalnız **review cadence**'i son toplu patch'e bağla; kabul taşınamaz ve owner emirleri kanıt yerine geçmez.
5. Üç kanonik belge, Worker/Supervisor revizyonları, `AGENTS.md` ve cross SHA-256 kilitleri **birlikte**, ayrı yetkili değişiklik olarak güncellenir. Kilitler yeni kapsamı gizlemek için değil yeni onaylı release'i doğrulamak içindir.
6. B9-F02/F03 ve C stage source/method gereksinimleri **aynen kalır**. Formül, tolerans, materyal, kural kapsamı veya full-column PASS asla buradan çıkarılamaz.

## Release gate

Değişiklik sahip tarafından ratify edilene ve Supervisor gerekli bağımsız G0/G1/G2/C incelemesini tamamlayana kadar bu CR, C1 taslağını `main`e otomatik merge etmeye, `ACCEPTED_AB` vermeye, normatif kolon PASS üretmeye **yetki vermez**.

**Sıradaki kayıt:** CR uygun hale geldiğinde approved sürüm hash'leri, tam doküman patch'i, exact HEAD/TREE ve test kanıtı tek bağlantıyla bu klasöre eklenir; bu dosya sessiz ratifikasyon yaratmaz.
