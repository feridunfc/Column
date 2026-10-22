# Column — Worker görevi: Adım A ve Adım B

task_id: COLUMN-AB-IMPLEMENTATION-1.3  
release_id: COLUMN-OOP-1.3-20261022  
constitution_version: 1.3.0  
constitution_path: docs/architecture/COLUMN_CONSTITUTION.md  
constitution_sha256: 38b63b66896e273112e1a075b3acb8d2727475760512b8532299bebab5993c00  
canonical_path: docs/tasks/COLUMN_WORKER_AB.md  
role: IMPLEMENTER  
status: READY_FOR_SUPERVISED_EXECUTION / NOT_EXECUTED

## 1. Bağlayıcı başlangıç talimatı

`feridunfc/Column` üzerinde tek uygulayıcı Worker’sın. Önce kök `AGENTS.md`, sonra anayasanın **tamamı**, sonra bu görev okunacak. Anayasa okunmadan plan, kod değişikliği, yeni test beklentisi veya tasarım kararı üretilmeyecek. İlk salt okunur repo tespiti ve başlangıç kaydı hazırlamak serbesttir.

Anayasa C-01…C-32 bağlayıcıdır. Bu görev anayasaya istisna getirmez. Özet, eski sprint promptu, mevcut kod veya “daha iyi olur” gerekçesiyle karar değiştirme. Çelişki varsa ilgili işi durdur ve tam maddeyle bildir. Kullanıcının açık yeni kararı varsa C-02 sürüm güncellemesini iste; eski hash’i geçersizken çalışmayı sürdürme. Routine uygulama ayrıntılarını anayasa içinde kendin çöz; kullanıcıdan her dosya için onay isteme.

Göreve başlamadan:

```bash
git status --short
git rev-parse HEAD
git rev-parse HEAD^{tree}
python tools/check_architecture_contract.py
python -m unittest discover -s tests -v
```

`HEAD^{tree}` komutunu kullanılan shell gerektiriyorsa tek tırnakla geçir. Çalışma ağacındaki önceki değişiklikleri silme, `reset/clean` yapma. Hash kapısı başarısızsa çalışmayı durdur. Başlangıç testindeki mevcut başarısızlıkları kaydet; sessizce baseline sayma veya ilgisiz işlere yayılma. Supervisor kapsam ve etkisini değerlendirir.

Okuma/başlangıç kaydını `local_out/column_ab/bootstrap.json` içinde üret; projedeki mevcut çıktı politikası farklıysa onu koru. Alanlar: `role`, `task_id`, `release_id`, `branch`, `base_head`, `base_tree`, `constitution_version`, `constitution_sha256`, `task_sha256`, `read_complete`, `scope`, `baseline_tests`. Ayrıca iç birimler, public sonuç sınırı, kanıt kabulü, kernel erişimi ve ertelenmiş kapsam için kendi cümlelerinle beş kısa kural yaz. `read_complete=true` ancak tam okuma sonrasında yazılır; hash hesabı okumak yerine geçmez.

Supervisor’a tek mesajda başlangıç kaydı, aşağıdaki izinli dosya planı, kabul matrisi ve baseline sonucunu ilet. **G0 kabulünden önce uygulama koduna başlama.** Bu belge kendi kendine Supervisor kabulü üretme yetkisi vermez. Supervisor oturumu yoksa G0 beklediğini açık bildir; onay uydurma.

## 2. Amaç ve kesin kapsam

Tek uçtan uca hedef:

`typed SectionCapacityProblem -> application.calculate_section -> SectionSolver -> SectionKernelAdapter -> existing physics -> SectionCapacityResult -> same JSON + HTML`

İki farklı gerçek boyuna donatı düzeni aynı public yoldan çalışmalıdır. API fixture adına veya tek kesite hardcode edilemez. Çıktı kesit sayısal sonucudur; kolon/bina/yönetmelik PASS değildir.

Bu görevde kolon tasarımı, aday araması, kat/birleşim hesabı, canlı ETABS, analiz/model değişikliği, genel veri tabanı veya cache sistemi yoktur. Bu gelecek servisleri boş kabuklarla kodlama. `check_column` ve `design_column` girişlerini uygulanmış gibi dışa açma.

## 3. Dosya ve bağımlılık planı

| Alan | İzinli sorumluluk |
|---|---|
| `tbdy_column_core/domain/quantities.py` | Kanonik miktarlar ve Angle |
| `tbdy_column_core/domain/tolerances.py` | Boyutlu sayısal politika |
| `tbdy_column_core/domain/identity.py` | Revizyonlu kaynak/kural/kanıt referansları |
| `tbdy_column_core/domain/coordinates.py` | Nokta, sağ elli eksen, altı bileşenli eylem ve açık referans dönüşümü |
| `tbdy_column_core/domain/stations.py` | StationRef / StationGeometry / StepIdentity / ResponseKey |
| `tbdy_column_core/domain/analysis_bundle.py` | Rol ve kaynak boyutları; kapsama bağlı kabul sözleşmesi |
| `tbdy_column_core/domain/outcomes.py` | Bilgi durumları, kontrol başlıkları, kapsam ve hesap izi |
| `tbdy_column_core/domain/section_models.py` | Profil, malzeme, çubuk, layout, RCSection |
| `tbdy_column_core/domain/section_requests.py` | Kesit istek ve sonuç tipleri |
| `tbdy_column_core/engineering/section_adapter.py` | Mevcut section kernel’ine tek yeni erişim sınırı |
| `tbdy_column_core/engineering/section_solver.py` | Çözüm orkestrasyonu, gerçek kalan ve politika denetimi |
| `tbdy_column_core/application/services.py` | `calculate_section` facade |
| `tbdy_column_core/reporting/section_report.py` | Aynı sonuçtan JSON/HTML |
| `tests/test_column_contracts.py`, `tests/test_section_pilot.py` | Anayasa ve sayısal kabul senaryoları |
| `examples/section_pilot.py` | Aynı public API’yi kullanan iki düzenli çalıştırılabilir örnek |

Gerekli `__init__.py` ve küçük test yardımcıları eklenebilir. Birbiriyle çok yakın tipleri birleştirmek mümkün; public sözleşme, sorumluluk ve import sınırı korunmalıdır. Plan dışı dosya değişikliği gerekirse nedenini önce Supervisor’a bildir. Paketleme düzenini ve Python >=3.12 tabanını koru; gereksiz yeni bağımlılık ekleme.

Korunanlar: kök `AGENTS.md`, üç kanonik belge, `tools/check_architecture_contract.py` ve `tests/test_architecture_contract.py` kilitleri; mevcut kernel/test/API davranışı ve tarihsel kanıtlar. Worker, koruma testini silerek, skip ederek, digest’i yenileyerek veya beklenen değeri değiştirerek kendi sapmasını geçiremez. Kernel hatası bulunursa C-30’a göre ayrı kanıtlı düzeltme önerisi hazırlanır; doğrudan formül değiştirilmez.

## 4. Adım A — uygulanacak sözleşmeler

1. **C-08/C-09:** Değişmez ve sonlu miktarlar, doğru boyut aritmetiği, açık dış birim kurucuları, boyutlu toleranslar. `bool` kabul edilmez; aritmetik taşma da yakalanır. İki birim sisteminde aynı fiziksel girdi toleransla aynı sonucu verir.
2. **C-10:** Sağ elli ortonormal frame; fiziksel kuvvet/moment ile basınç pozitif kernel N işareti ayrımı. Analitik olarak doğrulanmış altı bileşenli dönme/öteleme fonksiyonu. Dönüşüm yalnız iki bağımsız işaret bayrağıyla yapılmaz.
3. **C-11:** Konum ve kimlik ayrı; aynı fiziksel koordinattaki iki farklı parça/yüz kaydı korunur. Tipli adım kimlikleri, run ve result-generation bilgisi kaybolmaz.
4. **C-12…C-15:** Üretici/edinim/amaç/tepki anlamı ayrımı; role/yönteme/tüketiciye/revizyona bağlı qualification. Kabul kapısı gerçek referans çözümlemesiyle en az geçerli kanıt, çözülemeyen kanıt ve yanlış kapsam/revizyon örneklerini ayırır. Dolu metin kontrolü tek başına yeterli değildir. Tam analiz import motoru yazılmaz.
5. **C-15/C-24:** `Provided`, `NotRequired`, `Missing`, `Unsupported`, `Unresolved`; eksikliği uygunsuzlukla karıştırmayan sonuç başlıkları. A/B’de uygulanmayan kontrol başlıkları kapsam dışı kalır; PASS olmaz.

A’nın değişmezlik/import sınırlarını ve anlamlı negatif durumlarını birlikte teslim et. Sadece constructor testi yazıp geçme. **G1: Supervisor A sözleşmelerini kabul etmeden B uygulamasına geçme.**

## 5. Adım B — kesit akışı

### Profil, donatı, malzeme

`RCSection`, tek geometrik profil, revizyonlu hesap malzemesi ve gerçek boyuna düzen taşır. A/B tam enine cage tasarlamaz. Paspayı tanımı C-17’ye uyar; çubuk kimlikleri, merkezleri, sınır ve çakışma doğrulanır. Malzeme katsayıları açık verilmiş model girdileridir. Per-bar `steel_ref` çözülür; farklı hesap yasaları tek çelikli kernel’e sessizce geçirilmez.

### Ayrışımlı istekler

`SectionCapacityProblem(section, request, numerical_policy, frame_model_contract, input_refs)` ve `SectionCapacityResult` tanımlansın. C-19’daki üç istek desteklensin:

- `AtStrainState`: açı ve c verilidir; N/M hesaplanır; hedef N kalanı uygulanmaz.
- `EnvelopeAtAxialForce`: hedef N için açı bazında kök çözümü ve gerçek kalanlar.
- `RadialCapacityAtAxialForce`: sıfır olmayan moment yönü için aynı N düzleminde kapasite.

Kısmi çözüm verisi korunur; tam zarf olmadığı açıktır. Sıfır yön, karma çelik ve desteklenmeyen politika için tanımlı sonuç üretilir. `inf` miktar veya JSON sayısı olmaz. Geçersiz public girdi tipli doğrulama sonucu; yazılımcı değişmez ihlali görünür teknik hatadır.

### Mevcut kernel ile bağ

İncelenen kaynak `Column@fc303e85b19c490a3dbbfbeb0bf67bd86c8d41ed` içindeki `physics/section_capacity.py` dosyasıdır. Gerçek checkout imzalarını yeniden doğrula. `evaluate_rectangular_column_capacity_state`, `solve_capacity_state_for_axial_force`, zarf ve radyal kapasite fonksiyonları dar adapter arkasındadır. `rebar_layout.py` içindeki yönetmelik filtreli aday üreticisi bu göreve alınmaz.

`max_iterations` için zarf yardımcı fonksiyonunun bunu kabul ettiğini varsayma. Gerekirse açı örneklerini üretip mevcut tek açı çözücüsünü çağır; matematiği kopyalama. Her gerçek N kalanı ilan edilen politikayla denetlenir. İlk kökün bulunması bütün köklerin çözüldüğünü göstermez. Kernel’in döndürmediği iterasyon/kök sayısını rapora yazma. Belirsizliği yapısal kapasite dışı hükmüne çevirmeme kuralı C-20’de bağlayıcıdır.

### Rapor

Aynı `SectionCapacityResult` üzerinden strict JSON ve okunabilir HTML üret. Başka formül yolu açma. Model, birim, aday/girdi referansı, istenen/uygulanan politika, kalan, açı çözünürlüğü ve destek eksikleri görünür olsun. Test malzemesini veya fixture’ı gerçek proje onayı diye gösterme.

## 6. Sabit sayısal fixture ve kabul testleri

Bu değerler sayısal referans girdileridir; otomatik normatif kabul değildir:

| Girdi | Değer |
|---|---|
| Kesit | b=40 cm, h=60 cm; kanonik 400×600 mm |
| Geometri | A=2400 cm²; I22=720000 cm⁴; I33=320000 cm⁴ |
| Beton/model | fck=35 MPa; fcd=35/1.5 MPa; k1=0.79; epsilon_cu=0.003 |
| Çelik/model | fyd=420/1.15 MPa; Es=200000 MPa |
| Düzen A | Dört Ø2 cm çubuk, (±15, ±25) cm |
| Düzen B | A’ya ek iki Ø2 cm çubuk, (-15,0) ve (15,0) cm |
| Paspayı/etriye | 3 cm temiz paspayı; 1 cm etriye çapı |
| Gerinim durumları | (0°, c=20 cm), (33°, c=24 cm), (90°, c=20 cm) |

Oracle üretim solver/adapter’ını çağırmaz. Mevcut `tests/independent/oracle.py` doğrudan durum, ayrı kök denetimi ve sık açılı radyal referans için kullanılır. Bu karşılaştırma aynı malzeme idealizasyonu altında sayısal denetimdir. `tests/test_ts500_numerical_oracles.py` varlığı yeni kesit pilotunun bütün kabulünü kendiliğinden sağlamaz.

| Test ID | Zorunlu davranış | Anayasa |
|---|---|---|
| AB-01 | `10 MPa * 100 cm² = 100 kN`; `100 kN * 20 cm = 20 kNm`; round-trip ve toleranslı birim eşdeğerliği | C-08, C-09 |
| AB-02 | Yanlış boyut/alan tipi, bool/NaN/Inf, sıfır boyut, taşma, negatif tolerans reddi | C-08, C-09 |
| AB-03 | Sağ elli dönüşüm, sol elli takım reddi, analitik r×F ve ters aktarım | C-10 |
| AB-04 | Aynı koordinatlı farklı parça/yüz kayıtları ve ResponseKey korunumu | C-11 |
| AB-05 | Aynı run fakat uygunsuz rol; farklı run fakat kanıtlı uyum; desteklenmeyen semantik | C-12, C-14 |
| AB-06 | Kaynak boyutları ayrı; çözülemeyen/yanlış kapsamlı kanıtla NotRequired/qualification kabul edilmez | C-13…C-15 |
| AB-07 | Profil alan/ataleti, paspayı, çakışma, yinelenen kimlik ve koordinat kontrolü | C-17 |
| AB-08 | Per-bar çelik çözümleme ve farklı hesap yasasında Unsupported | C-18 |
| AB-09 | İki düzende üç sabit gerinim durumu için bağımsız N/M2/M3 karşılaştırması | C-19, C-29 |
| AB-10 | Aynı fiziksel çubukların yeniden sıralanması sonucu değiştirmez; seçilmiş A/B farkı oracle ile örtüşür | C-17, C-29 |
| AB-11 | Bağımsız tek köklü hedef-N örnekleri, gerçek kalan ve politikanın gerçekten iletilmesi | C-09, C-20 |
| AB-12 | Örneğin 72/144/288 açıyla radyal yakınsama; sık oracle referansı; ayrı açısal hata bütçesi | C-20, C-29 |
| AB-13 | Sıfır yön, kısmi zarf ve sayısal belirsizlik doğru durum üretir; inf veya sahte FAIL yok | C-15, C-19, C-20 |
| AB-14 | Bağımsız hesaplanabilen sonuç, başka isteğin eksikliğiyle kaybolmaz; boş kapsam PASS olmaz | C-15, C-24 |
| AB-15 | Aynı nesneden JSON/HTML; strict JSON ve aynı revizyon/değerler | C-28 |
| AB-16 | Gerçek public facade, iki farklı düzen ve ikinci bir geçerli kesit girdisiyle hardcode olmadan çalışır | C-05, C-31 |
| AB-17 | Import sınırı ve değişmezlik; üretimde oracle/import veya gizli dış erişim yok | C-04, C-06, C-07 |
| AB-18 | Mevcut regresyonlarda yeni başarısızlık yok; belge hash kapısı korunmuş | C-30, C-32 |

Tolerans değerlerini test sonuçlarını gördükten sonra keyfî büyütme. Birim/doğrudan durum, kök dengesi ve açısal ayrıklaştırma için ayrı bütçe tanımla; seçimini yöntem ve yakınsama kanıtıyla gerekçelendir. Toleransın seçim kaydı G0 planında yer alır; gerekçeli düzeltme Supervisor’a bildirilir ve anayasadaki kabul sınırını değiştiremez.

## 7. Uyum matrisi ve teslim

Uyum defterinde C-01…C-32 için tam birer satır bulunacak: madde, A/B zorunlu parçası, uygulama dosyası/sembolü, test/inceleme kanıtı, HEAD ve durum. `SATISFIED` kanıtlanmış parça; `PRESERVED_DEFERRED` yalnız anayasada A/B dışı bırakılan parça; `VIOLATION` açık ihlal; `UNVERIFIED` kanıt yok demektir. Karma bir maddede zorunlu parça kanıtı ve ertelenen parça ayrı belirtilir. Ertelenmiş kod için boş sınıf üretme.

| Maddeler | A/B’de gereken |
|---|---|
| C-01…C-15 | Okuma/sürüm kapısı; katman, değişmezlik ve temel sözleşmelerin uygulanması |
| C-16 | Revizyonlu kimlik/çözümleme sınırını koru; bütün fiziksel model motorunu kurma. |
| C-17…C-20 | Kesit, malzeme, üç istek ve kernel/sayısal kalite tam uygulanır. |
| C-21…C-23 | Gelecek üye/trial/kat/birleşim sahipliğini koru; motorlarını uygulama. |
| C-24 | Sonuç başlıkları ve eksik/uygunsuz ayrımı uygulanır; kolon aday seçimi ertelenir. |
| C-25 | A/B’de arama yok; gelecekteki akışı bozacak gizli orkestrasyon ekleme. |
| C-26 | Bağımlılık/ref ve seri hale getirme uygulanır; DB/cache ertelenir. |
| C-27 | Native yasağına uy; native motor ertelenir. |
| C-28…C-32 | Aynı rapor, bağımsız kabul, regresyon ve Supervisor kapıları uygulanır. |

Commit’ler küçük ve incelenebilir olsun. G1 ve son G2 teslimleri belirli commit HEAD/tree’ye bağlıdır; testlerin ardından kod değişirse etkilenen doğrulamalar yenilenir. Supervisor onayı eski commit’ten yenisine taşınmaz.

Son teslimde başlangıç kaydı, değişen dosyalar, AB-01…AB-18 sonuçları, C-01…C-32 uyum defteri, gerçek test komutları/çıkışları, iki düzenin JSON/HTML örnekleri ve açık destek sınırlarını ver. `python -m examples.section_pilot` ile örnekler üretilebilir olmalı. Test çıktısı üretim hesabının kendisi gibi sunulmaz.

**G2 kapanışı yalnız Supervisor’ın bağımsız incelemesiyle `ACCEPTED_AB` olabilir.** Worker kendi kendine ürün veya mühendislik kabulü vermez. `VIOLATION`, zorunlu `UNVERIFIED`, uygulanmamış zorunlu test veya değiştirilmiş kilit varsa kapanış yoktur. C ve sonraki adımlara yeni görev olmadan geçilmez.
