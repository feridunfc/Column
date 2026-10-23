# C serisi — değiştirilmeyen kronolojik uygulama kaydı

Bir uygulama sprinti kapanırken **yeni** tarihli kayıt eklenir. Geçmiş çalışma/CI durumu sonradan sessizce yeniden yazılmaz. Yanlış geçmiş veri için yeni **CORRECTION** girişi yapılır. Ayrıntılı yapılandırılmış gerçeklik `SPRINT_LEDGER.json` içindedir.

## 2026-10-23 — C0: fiziksel kolon / tam cage — TESTED_DRAFT

- **Özgün kaynak:** `worker/v131-c0-physical-cage-draft-20261023@c3cf84fb39d6928b7bb069683945e0fa53f13787`.
- **Ana B11 sonrası yeniden taşınmış aday:** `worker/v132-c1-member-demand-20261023@7bb5f92fd47e048a4446e6e749b2531fdb3c4cfc`.
- **Değişen ürün:** `tbdy_column_core/domain/member_models.py`. Fiziksel alt/üst uç, boyuna çubukların gerçek ID'leri, gerçek etriye/çiroz, bölgesel enine donatı nüfusu; immutable `ColumnCandidate`, açık signed `ResponseKey` nüfus modeli.
- **Test:** `tests/test_c0_member_contracts.py`; 6 test, C1 birleşik 85 testlik CI matrisine dahil. Doğrudan C0 eski dalının sayısal B güvenliğini içerdiği iddia edilmez.
- **Sınır:** yalnız domain kontratları; PMM/shear/sargı/second-order/`check_column` yok. **Supervisor: PENDING**.

## 2026-10-23 — C1: kaynak nitelikli birinci mertebe talep derlemesi — TESTED_DRAFT

- **HEAD/TREE:** `7bb5f92fd47e048a4446e6e749b2531fdb3c4cfc` / `0e5d2ba38a77ccb7fdf7473e870d7db737c6a272`.
- **Değişen ürün:** `engineering/member_demand.py`, `tests/test_c1_member_demand.py`, `SPRINT_C1_MEMBER_DEMAND_CANDIDATE.md`.
- **Kanıt:** [GitHub CI 39939776094](https://github.com/feridunfc/Column/actions/runs/39939776094) Linux+Windows, Python 3.12/3.13, **4/4 SUCCESS, 85 unittest/hücre**.
- **Girdi/çıktı:** dışarıdan beklenen `ResponseKey` ve kaynak satırı ID'leri, `AnalysisBundle.qualify` verified scope, `StationGeometry`, `ActionVector`; altı bileşenli dönüşüm ve N işareti; `READY_FIRST_ORDER_ONLY/INCOMPLETE_SOURCE/UNQUALIFIED_SOURCE/INVALID_STATION_MAPPING`.
- **Negatif:** eksik kayıt korunur; yanlış role/run/generation/kanıt, yanlış fiziksel yüz, yanlış kaynak kimliği reddedilir; zarfı imzalı vektör olarak kullanma yasaktır.
- **Sınır:** sönüm/spektral, rijitlik, 2. mertebe ve yönetmelik PASS kapsam dışı. **Supervisor: PENDING**.

## 2026-10-23 — C kontrol mekanizması kurulumu — DOCUMENTATION_ONLY

- **Kaynak HEAD:** `7bb5f92fd47e048a4446e6e749b2531fdb3c4cfc` (C0/C1 ürün code taslağı).
- **Kapsam:** `docs/c_series/` içinde program planı, makine denetlenen ledger, insan kronolojisi, C-02 değişiklik isteği, final Supervisor handoff şablonu.
- **Korunanlar:** üç kanonik belge, AGENTS, test oracle, physics, main ve legacy. **C2 kodu bu işlemde başlatılmadı.**
- **Sonuç:** Journal commit'i/yeni CI sonucu bu kayda sonradan ayrı kanıt satırıyla iliştirilecek; bu satır henüz SUCCESS iddiası içermez.

## Yeni sprint için zorunlu kayıt şablonu

```text
DATE / SPRINT / STATUS:
BASE_BRANCH / BASE_HEAD / BASE_TREE:
IMPLEMENTATION_HEAD / IMPLEMENTATION_TREE:
CHANGED_PATHS / PUBLIC_CONTRACT:
C-XX CLAUSES / SOURCE VERSION / UNIT/FRAME/POLICY:
POSITIVE TESTS / NEGATIVE TESTS / INDEPENDENT ORACLE:
COMMAND / RUN_ID / CI MATRIX / OBSERVED RESULT:
KNOWN LIMITS / MISSING POPULATION / OPEN FINDINGS:
DEFECT FIXED? / NEW FINDING ID:
SUPERVISOR STATUS: PENDING until independent review
NEXT SPRINT PRECONDITIONS:
```
