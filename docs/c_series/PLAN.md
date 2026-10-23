# COLUMN — C Serisi kontrollü uygulama planı

**Mimari kaynak:** `COLUMN_CONSTITUTION.md` v1.3.1 C-01…C-32. **Bu dosya anayasanın yerini almaz.** Özellikle C-21–C-24, C-28–C-32 bağlayıcı hedeflerdir.

**Mevcut ana dal:** `main@9269a00f5f5471ab68413c039912cafb2cf4db39` (B1–B11 entegrasyonu). **C dalı:** `worker/v132-c1-member-demand-20261023` (ilk kaynak HEAD `7bb5f92fd47e048a4446e6e749b2531fdb3c4cfc`). **C0/C1:** kodlandı ve dört Linux/Windows 3.12/3.13 hücresinde 85 test/hücre geçen taslak, **Supervisor kabulü değil**.

## Kritik sınır — C-02 ve C-03

Mevcut v1.3.1 C-03, AGENTS ve Worker görev dosyası **yalnız A0/A/B uygulamasını etkin** ilan eder; C-31 ise C'de `check_column` hedefini belirtir. Kullanıcı C geliştirmesini ve en sonunda tek toplu Supervisor incelemesini talep etti. Bu talep **ayrı C-02 ChangeRequest** olarak kayda geçti; henüz üç kanonik belgeye uygulanmış ve kendi SHA kilitleriyle yayımlanmış v1.3.2 yoktur. Bu yüzden C0/C1 ve sonraki hazırlıklar **ayrık PR üzerinde taslak/deneysel çalışmadır**, sözleşme uygunluğu `ACCEPTED` değildir. Uygulama sınırını değiştirmek için sürüm, Worker/Supervisor görevleri, AGENTS ve SHA kilitlerinin aynı değişiklikte onaylı güncellenmesi gerekir; hiçbir kilit otomatik yenilenmez. Bu durum yeni formül veya normatif kural yazma gerekçesi değildir.

## Sprint planı (tek seri; D/E işleri karıştırılmayacak)

| Sprint | Teslim (dar sorumluluk) | Bitiş kriteri | Durum |
|---|---|---|---|
| C0 | Fiziksel kolon + tam cage | Enine bölgede boşluk/çakışma, sahte çiroz referansı, aday revizyonu değişmeden mutasyon reddi | TESTED_DRAFT |
| C1 | Kaynak bağlı birinci mertebe talepler | Eksik sonuç satırı, yanlış run/generation/role, sahte kanıt, zarf vektörü ve yanlış yüz eşlemesi reddi | TESTED_DRAFT |
| C2 | Scenario / Trial / MemberMechanics.geometry | Kat yüksekliğinden net boy üretme, I/J ile alt/üst takası, eksik boyu 0 veya L ile doldurma reddi | PLANNED |
| C3 | Stiffness + stability / second-order basis | Kanıtsız EI/k uç koşulu, atlanan veya iki kez uygulanan 2. mertebe, hedef kolonla tüm katın temsil edilmesi reddi | PLANNED |
| C4 | MemberDemandCompiler tam nüfus ve etki izleri | Case/step ve farklı kaynak runlarını gizli birleştirme; modal/zarfı eşzamanlı imzalı sayma; eksik dalı silme reddi | PLANNED |
| C5 | ColumnEvaluator + kontrol kapsamı | Numerical unresolved kapasiteyi PASS sayma, boş beklenen nüfus=PASS, etki olmadan PMM/second-order kontrol tamamlanmış gösterme reddi | PLANNED |
| C6 | Public check_column ve tek ColumnResult | Design aramasını gizlice başlatma; D/E kapsamını yapılan gösterme; kısmi kapsamdan ELIGIBLE/PASS üretme reddi | PLANNED |
| C7 | Bağımsız kanıt ve kapanış matrisi | Test sonucu = normatif onay; üretim değerini oraclea kopyalama; drift'i belge silerek saklama reddi | PLANNED |
| C8 | Supervisor toplu patch/disposition | Worker self-acceptance, kaynak hash değiştirerek PASS, açık VIOLATION veya UNVERIFIED ile release reddi | PLANNED |

**C-31 ürün ayrımı:** C = verilmiş cage ile `check_column`, talep üretimi/üye mekaniği. **D = kesme, sargı ve detaylandırma**; **E = katın tam nüfusu, birleşimler ve tam `ColumnResult`**; F = gerçek recorded model; G = native ETABS; H = toplu nüfus/performans. Bu ayrı adımlar C'de çözüldü diye gösterilemez. C public sonucu ancak `NOT_EVALUATED/MISSING_INPUT/UNSUPPORTED_METHOD` ile eksiklerini taşıyabilir; tam sistem uygunluğu/ELIGIBLE D/E gerektiren kapsamlarda yoktur.

## Tek sprintte sıralama / Definition of Done

1. **Başlangıç kimliği:** önceki HEAD + TREE, dal, korunan üç belge sürüm/hash’i, diff ve bilinmeyen dirty dosya durumu, kaynak referansları; kullanıcının çalışması temizlenmez.
2. **Sözleşme:** C-xx maddesi, public girdi/çıktı, gerçek fiziksel/analiz veri kaynağı, kapsam ve `Unsupported/Missing/Unresolved` davranışı sprint başlamadan yazılır. Gizli dış bağımlılık yok.
3. **İcra:** dar kod+test; kırmızı/negatif testler dahil. Normatif formül yalnız kontrol edilmiş kaynak/yöntem ve bağımsız denetimle; tahminî (EI), etkin boy, kombinasyon, koşul veya kesme kapasitesi yok. `physics` ve oracle değişiklikleri ayrı kanıtlı düzeltme olarak ele alınır.
4. **Kanıt:** komutlar/gerçek CI run URL ve sonuç, örnek N–mm–Nmm–MPa çıktıları, başarısızlık durumu, public işlev etkisi, açılan/kapanan finding ID. Test sayısı mühendislik kabulü sayılmaz.
5. **Kayıt:** `docs/c_series/SPRINT_LOG.md`'ye tarihli bir kayıt ve `docs/c_series/SPRINT_LEDGER.json`'a sprintin gerçek durumu, HEAD/TREE, dosyalar, kaynak/CI, kalan blokajlar eklenir. Önceki kayıt silinmez; düzeltme yeni kayıt olarak eklenir. Journal commit'i kendi HEAD'ini içeremez; uygulama commit'i ayrı bağlanır.
6. **Kapı:** geliştirici `TESTED_DRAFT`/ `BLOCKED` belirleyebilir, **`ACCEPTED` veremez**. Açık CR/uyumsuzluk dış sistem kabulüne taşınmaz. Sprint ilerleme kararı ayrıca yetkilendirilmiş draft çalışma içindir.
7. **Toplu Supervisor:** en sonda tek diff/patch paketi (küçük sprint commitleri bozulmadan), her sprint source HEAD/TREE ve kanıt, C-01…C-32 uyum matrisi, B9-F02/F03 ve C-02 sapma kuyruğu, bağımsız Supervisor kararları. Bağımsız onaysız main merge, `ACCEPTED_AB`, tasarım PASS yok.

## Sabit tasarım yasakları

- Fiziksel alt/üst uç, analiz I/J değil; merkez/net/serbest/etkin uzunluk birbirine varsayımla eşitlenmez.
- Kaynak ham N,V2,V3,T,M2,M3 imzalı birlikte oluşan vektördür; zarf/mod/yön maksimumlarından sahte eşzamanlı kayıt üretilmez.
- Beklenen case/step/istasyon/yüz/yön nüfusu **dışarıdan tanımlanır**; eksik satır PASS veya otomatik sıfır değildir.
- Second order: global ve yerel, yön, yöntem ve kaynak rolü izlenir; iki kez uygulama ya da atlama kapanmadan PASS yok.
- İstek/uygulanan policy, malzeme/model revizyonu, girdi fingerprint'i; çalışmış kontrol ile ertelenmiş kontrol ayrıdır.
- `check_column` ile `design_column` ve candidate seçimi birbirinden ayrıdır; ilk sürüm cage değiştirmez.
- Belge/CI kilidi, `AGENTS.md`, constitution hash testi veya legacy referansları kabul elde etmek için sessizce değiştirilmez.

**Her sprintin kalıcı başlangıç/teslim kanıtı:** `SPRINT_LEDGER.json` (makine kontrolü) + `SPRINT_LOG.md` (insan okunur kronoloji). `SUPERVISOR_BATCH_HANDOFF.md` toplu kapanış dizinidir.
