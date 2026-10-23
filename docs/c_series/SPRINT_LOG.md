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

## 2026-10-23 — C2: scenario/trial + fiziksel geometrinin hazırlanması — TESTED_DRAFT

- **Parent C kontrol HEAD/TREE:** `d33f5dba56ad71ff150353781c6607751ab019bf` / `1e7996b463b381eeb7bf6852b9fb8f449c98bab8`.
- **C2 implementation HEAD/TREE:** `5892f175c674ff29900ca48c61c5b60fcf2070d4` / `51efa895ef20a467ece4fa32a89bc54f817e0ecf`.
- **Değişenler:** `domain/scenario.py`, `engineering/member_mechanics.py`, `tests/test_c2_scenario_geometry.py`, `docs/c_series/SPRINT_C2_GEOMETRY.md`. Fiziksel üye ve scenario revizyonları, tek kolonun `TrialContext` üzerinde seçili cage'i, gerçek 3D centerline ve açık kaynaklı ayrı clear/unbraced/effective length kayıtları.
- **Test/kanıt:** [GitHub Actions 39941320817](https://github.com/feridunfc/Column/actions/runs/39941320817) **4/4 SUCCESS**, Ubuntu/Windows Python 3.12/3.13, **95 unittest/hücre** (7 yeni C2 testi). Codespaces'teki eski 88/88 testi `d33f5d...` HEAD için PASS; yeni C2 eklemesi için Codespaces sonucu henüz verilmedi.
- **Pozitif:** senaryo/üye/cage kaynak revizyon eşleşmesi, fiziksel alt/üst yüz, bağımsız net ve serbest uzunluk girdileri, trial aday revizyonu değiştiğinde kaynak senaryonun değişmemesi.
- **Negatif:** eksik clear/unbraced/effective boydan otomatik değer türetilmiyor; doğrulamasız etkin boyun stiff/second-order hazır sayılması reddediliyor; 3D centreline'ı aşan declared clear length, aynı length kind duplikasyonu, yanlış üye hedefi, iki assignment, yanlış aday identity reddediliyor.
- **Güvenlik sınırı:** yalnız `PHYSICAL_GEOMETRY_DECLARED_ONLY`; `stiffness_ready=False`, `second_order_ready=False`. Ne TS500/TBDY 2. mertebe, ne normatif k, ne `check_column`/PASS eklendi.
- **Açık:** C-02 sürümlü kapsam ratifikasyonu yok; G0/G1/G2 `PENDING`; B9-F02/F03 `OPEN`. **Supervisor: PENDING; merge/release: HOLD.**

## 2026-10-23 — C3: EI, kat ve ikinci-mertebe kaynak nüfusu — IMPLEMENTED_UNTESTED

- **BASE:** `e560b825003b44855f3b19091f90c106d06ccc92` (TREE `1abda87cf2944c7aa951b7d0686d8fd59f700c11`); ayrı `worker/v132-c3-c8-column-candidate-20261023` dalı.
- **Kod:** `engineering/stability.py` gerçek source-bound EI, x2/x3 ve GLOBAL_P_DELTA/LOCAL_P_DELTA yöntem-kanıt-id ve tam kat üye nüfusu; `MemberMechanics.prepare_stiffness/resolve` başvuruları.
- **Koruma:** kanıtsız/eksik EI, eksik kat nüfusu, eksik veya uyuşmayan second-order run ve yöntem açık issue; sonuç `DEPENDENCY_DECLARED_UNRESOLVED`. Hesaplanmış ikinci mertebe/TS500 uygunluğu iddiası yok.
- **TESTS:** sahibi C8 sonrasına erteledi; **BU SPRINT TEST EDİLMEDİ**. Supervisor PENDING, CR-C02 açık.

## 2026-10-23 — C4: kaynak ve etki dallarının birleştirilmesi — IMPLEMENTED_UNTESTED

- **BASE:** `46c4ff91ac648a26c6375ca3330f3d4b0a3eff67`; `engineering/full_member_demand.py` eklendi.
- **Kod:** ilk mertebe C1 `MemberDemandCompiler` çıktısı aynen korunur. Beklenen P-Delta/P-delta eksen ve yöntem dalları dışarıdan sabit nüfusla gelir; fiziksel kaynak `ResponseKey`, analiz run/generation, `RuleRef`, `EvidenceRef` eşleşmesi zorunludur.
- **Risk kontrolü:** her kaynaklı altı-vektör kendi koordinat/referansıyla taşınır; birbirinden farklı veya zarf/modal maksimumlarından sahte imzalı vektör üretilmez. Kaynağı doğrulanmamış ikinci mertebe etkisi uygulanmaz ve `second_order_approved=False` kalır.
- **TESTS:** C8 sonrasına ertelendi; `IMPLEMENTED_UNTESTED`. Supervisor PENDING; B9 ve C-02 açık.

## 2026-10-23 — C5: ColumnEvaluator / kapsamlı kolon sonucunun iskeleti — IMPLEMENTED_UNTESTED

- **BASE:** `d98dbdc780e2a8c796ca4697900e549d21e4976f`. `engineering/column_evaluator.py` eklendi.
- **İş:** yalnız açık `demands_outcome` alır, compilerı gizlice çağırmaz. `ColumnEvaluationProblem` senaryo ve hedef candidate revizyonu doğrular. Kontrol nüfusu dışarıdan ilan edilir; GEOMETRY/PMM/SECOND_ORDER ve D/E başlıkları birbirinden ayrılır. `CandidateResult` risklere göre `UNDETERMINED` ve `CheckResult` ayrı applicability/execution/compliance/coverage/freshness taşır.
- **Sınır:** C5 henüz kaynaklı istasyon frame ve tam second-order sağlamadığından `NUMERIC_PMM_FRAME_SOURCE_NOT_PRESENT_IN_EVALUATOR` açık olarak işaretlidir; gerçekte yapılmamış PMM kontrolü sayısal başarı gibi gösterilmez. `full_column_pass=False`, `NOT_EVALUATED`.
- **Test:** C8 sonrası toplu koşu için ertelendi; bu commit `IMPLEMENTED_UNTESTED`.

## 2026-10-23 — C6: public check_column + tek ColumnResult/JSON/HTML — IMPLEMENTED_UNTESTED

- **BASE:** `4e6da09fb20ded6d19f824d4ba63963e21149b95`.
- **Kod:** `application/column_check.py` açık tek yönlü C2→C3→C4→C5 akışını ve kaynak bağlı `CheckRequest`/değişmez `ColumnResult` değerini kurar. `application/services.py` içinden public `check_column` erişimi verilir. `reporting/column_report.py` aynı sonuçtan strict JSON ve escaped HTML üretir.
- **Sınır:** tasarım araması, ETABS API, ikinci-mertebe hesap, kesme/sargı, birleşim veya normatif PASS yok. Sonuç `INCOMPLETE_NOT_CODE_APPROVED` ve tüm kaynak/coverage meselelerini taşır. `ColumnResult` tüm zorunlu check başlıklarını kaybetmeden korur.
- **TESTS:** C8 sonrası toplu koşu için ertelendi; `IMPLEMENTED_UNTESTED`. Supervisor ve merge PENDING.
