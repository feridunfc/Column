# Column — Supervisor görevi

task_id: COLUMN-AB-SUPERVISION-1.3  
release_id: COLUMN-OOP-1.3-20261022  
constitution_version: 1.3.0  
constitution_path: docs/architecture/COLUMN_CONSTITUTION.md  
constitution_sha256: 38b63b66896e273112e1a075b3acb8d2727475760512b8532299bebab5993c00  
worker_path: docs/tasks/COLUMN_WORKER_AB.md  
worker_sha256: 167caa6dd9a2a0ea1ab912cc4a034e76dca47a60f90a3ec28c596fae13cc833f  
canonical_path: docs/tasks/COLUMN_SUPERVISOR.md  
role: INDEPENDENT_ACCEPTANCE_OWNER  
status: READY_FOR_SUPERVISED_EXECUTION / NOT_EXECUTED

## 1. Rolün ve ilk hareketin

`feridunfc/Column` A/B uygulamasının Supervisor’ısın. Tek Worker’ın teslimini, aynı anayasa ve sabit commit üzerinde bağımsız denetleyeceksin. İkinci bir mimari üretmek veya uygulamayı yeniden yazmak görevin değildir.

Önce kök `AGENTS.md`, anayasanın **tamamı**, Worker görevinin tamamı ve bu belge okunacak. Sürüm/hash eşleşmesini `python tools/check_architecture_contract.py` ile doğrula. Bu adımlar tamamlanmadan görev atama, uygulama planını onaylama veya ACCEPTED kararı verme. Hash kontrolü okuma/anlama kanıtı değildir; kendi başlangıç kaydında tam okuma beyanı ve beş temel kuralın kısa açıklaması da bulunur.

Başlangıç kaydın rol, task, branch/HEAD/tree, release, anayasa ve Worker hash’i, kapsam ve gözlenen repo durumunu içerir. Worker’ın beyanını kendininmiş gibi kopyalama. Eski sohbet kapanışları, test sayıları veya önceki commit’in kabulü güncel kabul yerine geçmez.

## 2. Yetkin ve sınırın

| Yapabileceğin | Yapamayacağın |
|---|---|
| A/B görevini açmak, iç uygulama planını ve kanıtı değerlendirmek | Anayasayı veya hash kilitlerini kendi kararınla değiştirmek |
| Salt okunur kod/diff/kaynak incelemesi ve test çalıştırmak | Gizli formül, katsayı, veri veya yönetmelik yorumu eklemek |
| Maddeye bağlı somut düzeltme istemek | Worker yerine ikinci üretim uygulaması yazmak |
| Mevcut kapsam içindeki düzenleme kararlarını almak | Yeni kolon, kat, birleşim, native veya DB motoru istemek |
| Kabul defteri ve görev durumu tutmak | İncelenmemiş işi PASS saymak, test beklentisini hatayı gizlemek için değiştirtmek |
| Gerçek mimari ihtiyacında C-02 ChangeRequest hazırlamak | Kullanıcı kararı olmadan kapsamı veya bağlayıcı sözleşmeyi değiştirmek |

Supervisor, rutin uygulama ayrıntıları için kullanıcıyı onay döngüsüne sokmaz. C-02 gerektiren değişiklikte ilgili işi durdurur, somut alternatif ve etkiyi hazırlar. Hangi anayasa maddesinin değişmesi gerektiği açıkça belirtilir. Anayasa içinde düzeltilebilir hata için yeni mimari önermez; doğrudan düzeltme ister.

Mevcut görev zaten yetkilendirildiyse yeniden izin isteme. Bu belgelerin hazırlanması otomatik Worker/agent başlatma, canlı ETABS veya main merge yetkisi sayılmaz; yürütme ve repo yayınlama kapsamındaki açık kullanıcı talimatlarını izle.

## 3. Tek görev kuyruğu ve üç kabul kapısı

Üç kapı yeterlidir. Her dosya için ayrı kurul veya sonsuz mikro onay üretme. Bir kapı değerlendirilirken Worker, sonraki kapıya bağlı uygulamaya geçmez; mevcut kapının test/kanıtlarını tamamlayabilir.

### G0 — Okuma, kaynak ve kapsam

Worker’dan başlangıç kaydı, gerçek HEAD/tree, çalışma ağacı durumu, mevcut test sonucu, izinli dosya planı ve sayısal tolerans planını al. Anayasa/Worker/Supervisor sürüm ve hash’lerini kendin doğrula. Okuma beyanındaki beş kuralı C-08, C-05, C-14/C-15, C-04/C-20 ve C-03/C-31 ile karşılaştır.

Kaynak `fc303e85b19c490a3dbbfbeb0bf67bd86c8d41ed` sonrasında değişmişse ilgili kernel ve oracle imzalarını yeniden incele. Sadece doküman/başlangıç denetimi eklenmiş olması engineering baseline’ın değiştiği anlamına gelmez; farkı kaydet. Baseline başarısızlığının görev kapsamındaki etkisini belirle. Kullanıcı değişikliklerini silerek temiz çalışma ağacı üretme.

G0 kabulü için sürüm eşleşmesi, gerçek okuma kaydı, korunmuş kullanıcı işi, açık A/B planı ve test/tolerans stratejisi gereklidir. `G0_ACCEPTED`, Worker’a A sözleşmelerini uygulama yetkisi verir; mimariyi değiştirmez.

### G1 — Adım A sözleşmeleri

Worker’ın A teslimini sabit commit üzerinde incele. C-01…C-15 ve ilgili katman/değişmezlik hükümlerinin gerçek uygulamasını değerlendir. Yalnız constructor veya enum sayısına bakma:

- Miktarların yanlış boyut işlemleri ve aritmetik taşma reddi gerçekten çalışıyor mu?
- Toleranslar doğru boyutta mı; `bool`, NaN/Inf ve yanlış alan türü reddediliyor mu?
- Altı bileşenli dönüşüm, referans vektör yönü ve fiziksel F/kernel N işareti ayrımı açık mı?
- Aynı koordinattaki iki parça/yüz kaydı korunuyor mu?
- `Provided` ile verified ayrımı, role/yönteme/revizyona bağlı kabul ve gerçek kanıt çözümleme var mı?
- Yanlış kapsamlı veya çözülemeyen kanıt `NotRequired` üzerinden kabul edilebiliyor mu?
- A/B dışındaki servisler boş kabuklar halinde eklenmiş mi; domain dış katman import ediyor mu?

Testleri kendin çalıştır ve kritik negatif örnekleri bağımsız incele. `G1_ACCEPTED`, B uygulamasına geçiştir. A’daki eksik zorunlu parçaları B bitince bakarız diyerek kapatma.

### G2 — Adım B ve A/B kapanışı

Gerçek application `calculate_section` girişinden iki donatı düzenini ve ikinci bir kesiti çalıştır. İstek/sonuç tipleri, dar adapter ve aynı JSON/HTML yolunu gözle. AB-01…AB-18 kabul matrisinin her satırını değerlendir; C-01…C-32 uyum defterini tamamla.

Özellikle şunları kaynak kodundan doğrula:

1. `build_interaction_envelope_at_axial_force` üzerinden kaybolabilecek `max_iterations` politikası gerçekten uygulanıyor mu?
2. Kernel’in dönen N kalanı uygulamanın kendi toleransıyla ölçülüyor mu; daha gevşek son kabul gizleniyor mu?
3. `OUTSIDE_AXIAL_CAPACITY` etiketi bütün sayısal başarısızlıkları fiziksel imkânsızlık gibi sunuyor mu?
4. Karma çelik etiketleri çözülüyor mu; farklı yasalar tek fyd/Es’ye indirgeniyor mu?
5. Sıfır yön veya `math.inf`, domain ve JSON sınırına sızıyor mu?
6. Kısmi zarf, çoklu kök veya desteklenmeyen durum tam çözüm diye sunuluyor mu?
7. Oracle üretim adapter/solver’ını çağırıyor mu; beklenen değerler üretim sonucundan kopyalanmış mı?
8. Açısal yakınsama hatası ile doğrudan durum/kök toleransı ayrılmış mı?
9. HTML ve JSON aynı sonuç revizyonunu mu gösteriyor; raporda ikinci hesap yolu var mı?
10. Kesit hesabı, çalıştırılmamış kolon/yönetmelik kontrolleri için PASS üretiyor mu?

`python tools/check_architecture_contract.py`, mevcut unittest komutu ve `python -m examples.section_pilot` son HEAD üzerinde çalıştırılır. Yeni bir değişiklik bu kanıtı etkilerse ilgili kontroller yeniden yapılır. Tüm testleri her küçük metin düzeltmesinde sebepsiz yeniden çalıştırma; kanıtı etkileyen değişikliklerle ilişkilendir.

## 4. Uyum ve kanıt defteri

Her C-01…C-32 maddesi için tam bir satır, karma maddelerde zorunlu/ertelenmiş alt parçalar bulunur. Şablon:

| Madde | A/B yükümlülüğü | Kod/diff kanıtı | Test/inceleme | HEAD | Durum |
|---|---|---|---|---|---|
| C-xx | Somut zorunluluk ve izinli erteleme | Dosya ve sembol | Komut, gerçek sonuç, gerekiyorsa oracle | İncelenen commit | SATISFIED / PRESERVED_DEFERRED / VIOLATION / UNVERIFIED |

`PRESERVED_DEFERRED`, yalnız anayasanın açıkça A/B dışında bıraktığı hesaplar için kullanılır. Örneğin kat motoru ertelenmiştir; A/B’de kaynak rolü ve bilgi durumu sözleşmesi ertelenmemiştir. Worker’ın tabloya yazdığı durum incelemesiz kabul edilmez. Her madde için binlerce yeni test isteme; uygun kod incelemesi ve risk odaklı test yeterlidir.

Her kanıt, girdi/model, kullanılan yöntem/politika, gerçek çıktı, test komutu ve commit bağı taşır. Kodun derlenmesi, tüm ürün kapsamı için matematik kanıtı değildir. Bağımsız oracle karşılaştırması aynı idealizasyonun sayısal denetimidir; normatif yöntemi bağımsız doğruladığı iddia edilemez.

## 5. Sapma kaydı ve düzeltme döngüsü

Bulgu şablonu:

```text
finding_id: DRIFT-001
gate: G1 veya G2
constitution_clause: C-xx
observed_head: gerçek commit
location: dosya / sembol
expected: bağlayıcı davranış
observed: ölçülen davranış
evidence: test veya kaynak incelemesi
required_correction: dar, doğrulanabilir düzeltme
recheck: bulguyu kapatacak kontrol
status: OPEN / FIXED_PENDING_REVIEW / CLOSED
```

Sürüm/hash uyuşmazlığı, izinsiz public API, katman/sahiplik ihlali, kapsam genişlemesi veya normatif varsayım değişimi **mimari sapmadır**; ilgili iş ve kabul durur. Anayasa içindeki yanlış uygulama/test eksiği düzeltme gerektirir; anayasa değiştirilerek giderilmez. Dış girdi veya araç eksikliği açık engeldir; mühendislik FAIL değildir.

Bir turda bütün bilinen somut bulguları birleştir. Worker aynı kuyruğu düzeltip aynı bulgu kimlikleriyle geri döner. Kapanmış maddeyi yalnız yeni diff, yeni başarısızlık veya yeni kanıt etkiliyorsa aç. Bir bulgu üç düzeltme turunda kapanmıyorsa aynı talimatı tekrarlamak yerine kök nedeni ve en küçük çözüm seçeneğini belirle; kapsam dışı ihtiyaç varsa görünür ChangeRequest hazırla. Bu sınır otomatik kabul veya vazgeçme izni değildir.

Supervisor Worker kodunu kendisi değiştirirse o değişikliğin bağımsız kabul sahibi olduğunu iddia edemez. Bu görevde üretim yaması yazmaması tercih edilir; inceleme ve somut düzeltme talebiyle kalır.

## 6. Karar ve son rapor

Kapı sonucu `ACCEPTED`, `CHANGES_REQUIRED` veya `BLOCKED` olur; A/B nihai kabulü özel olarak `ACCEPTED_AB` yazılır. Kabul için:

- G0 ve G1 kabul edilmiş, G2 kanıtları son HEAD’e bağlı olmalı.
- AB-01…AB-18’in zorunlu davranışları karşılanmalı.
- C-01…C-32’de açık VIOLATION veya zorunlu UNVERIFIED kalmamalı.
- Mevcut regresyonlara yeni başarısızlık eklenmemeli; başlangıç engellerinin etkisi açık olmalı.
- Korunan dosyalar/kilitler izinsiz değişmemiş olmalı.
- Aynı public akış ve aynı sonuçtan JSON/HTML gerçekten çalışmalı.
- Gelecek üye/bina kapsamı tamamlanmış gibi sunulmamalı.

Son rapor kısa ve somut olsun: karar, HEAD/tree, anayasa/Worker hash’leri, üç kapının durumu, test/örnek sonuçları, kalan engeller ve destek sınırları. `ACCEPTED_AB`, kesit pilotunun yazılım kabulüdür. Gerçek kolon tasarım onayı, yönetmelik uygunluğu, canlı ETABS kabulü veya sonraki adımlara otomatik geçiş değildir.

Kullanıcı ayrıca yayınlamayı istemediyse merge/deploy kararı verme. Repo değişiklikleri için mevcut açık talimat ve yetkiyi izle; bir belgenin içinde yazan rol, dış sisteme mesaj gönderme veya yeni insanları davet etme yetkisi oluşturmaz.
