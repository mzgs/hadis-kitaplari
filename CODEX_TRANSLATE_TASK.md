# Codex Hadis Çeviri Görev Talimatı

Bu dosya Codex'e doğrudan verilecek çeviri görevleri için hazırlanmıştır.

Amaç: Codex, belirtilen `sunnahcom/*.json` kaynak dosyasındaki hadisleri kendisi okuyup Türkçeye çevirecek, mevcut çeviri dosyalarına dokunmayacak, sadece eksik olanları ekleyecektir.

Bu talimat `translate_chatgpt_web.py` veya `test_translate_chatgpt_web.py` için değildir. Codex bu dosyayı bağımsız görev talimatı olarak kullanmalıdır.

## Görev Yorumu

Kullanıcı şöyle bir istek verebilir:

> Bu dosyayı dikkate alarak `sunnahcom/bukhari.json` ilk 20 hadisi çevir.

Codex bunu şu şekilde yorumlamalıdır:

1. Kaynak dosya: `sunnahcom/bukhari.json`
2. Hadis aralığı: `1-20`
3. Çıktı klasörü: `translations/bukhari/`
4. Çıktı dosyaları: `translations/bukhari/1.json` ... `translations/bukhari/20.json`
5. Var olan dosyalar atlanır.
6. Sadece eksik dosyalar Codex tarafından çevrilip eklenir.
7. Sonunda hangi dosyaların eklendiği ve hangilerinin zaten mevcut olduğu raporlanır.

## Mevcut Dosyaları Koruma

- Mevcut çeviri dosyaları silinmez.
- Mevcut çeviri dosyalarının üzerine yazılmaz.
- Mevcut dosyalar yeniden çevrilmez.
- Kullanıcı açıkça “yeniden çevir”, “üzerine yaz”, “force uygula” veya benzeri bir talimat vermedikçe yalnızca eksik dosyalar oluşturulur.
- Çıktı klasörü yoksa oluşturulur.

## Kaynak Okuma

Codex kaynak JSON'u kendisi okur.

Kaynak yapısı genellikle şöyledir:

- Ana nesnede `books` alanı bulunur.
- Her kitap içinde `content` listesi bulunur.
- Hadisler sıralı olarak bu `content` listelerinin birleşiminden elde edilir.
- Hadis numarası, bu birleşik listenin 1 tabanlı indeksidir.

Her hadis kaydında genellikle şu alanlar vardır:

- `arabic`
- `english`
- `reference`

Çeviride ana kaynak `arabic` alanıdır.

## Çıktı Formatı

Her hadis ayrı bir JSON dosyası olarak yazılır:

```json
{
  "tr": "<Türkçe çeviri>",
  "reference": "<kaynak reference değeri>",
  "grade": ""
}
```

Kurallar:

- JSON geçerli olmalıdır.
- Sadece `tr`, `reference`, `grade` alanları bulunmalıdır.
- Bütün değerler string olmalıdır.
- `reference`, kaynak hadisteki `reference` değeriyle birebir aynı olmalıdır.
- Kaynak kayıtta açık bir sıhhat hükmü yoksa `grade` boş string olmalıdır.
- Sıhhat hükmü tahmin edilmez.
- Âlimlere kaynaksız hüküm nispet edilmez.

## Çeviri Öncelikleri

Öncelik sırası:

1. Arapça metindeki anlamın eksiksiz ve doğru aktarılması
2. Hadisin maksadının, vurgu derecesinin ve konuşmacılarının korunması
3. Türkiye’de yerleşik hadis tercümesi terminolojisi
4. Doğal, açık ve akıcı Türkçe
5. Klasik hadis tercümesi üslubuyla ölçülü uyum

## Kaynak Kullanımı

- Arapça metin tek yetkili çeviri kaynağıdır.
- İngilizce alan varsa yalnızca çeviri bittikten sonra eksiltme veya yanlış anlamayı fark etmek için kontrol amacıyla kullanılabilir.
- İngilizce ifadeler Türkçeye birebir aktarılmaz.
- Arapçaya aykırı hiçbir unsur çeviriye eklenmez.
- Kaynakta açıkça bulunmayan sûre adı, âyet numarası, tarih, yer, kişi kimliği veya açıklama tahmin edilmez.

## Anlam Sadakati

- Metindeki hiçbir olay, şart, istisna, sebep, sonuç, yemin, olumsuzluk, karşılaştırma, üstünlük derecesi, zamir ilişkisi veya konuşma sırası atlanmaz.
- Konuşmacılar açık tutulur.
- Resûlullah’ın sözü ile râvinin açıklaması birbirine karıştırılmaz.
- Uzun rivayetlerde olay akışı korunur.
- Anlamı değiştiren sadeleştirme yapılmaz.
- Metinde olmayan yorum veya tarihî açıklama eklenmez.

## İsnad ve Rivayet Yapısı

- Hadisin başındaki uzun teknik râvi zincirini bütünüyle çevirmek zorunlu değildir.
- Çeviri, hadisi aktaran son sahâbî veya anlamlı râviden başlatılabilir.
- Hadis metni içindeki râvi açıklamaları, konuşmalar, ek bilgiler ve olay örgüsü atlanmaz.
- `عن فلان` kalıbı bağlama göre şöyle aktarılır:
  - “Falancadan rivayet edildiğine göre”
  - “Falanca şöyle rivayet etmiştir”
- Resûlullah’ın sözleri için genellikle “buyurdu” kullanılır.
- Sahâbî ve diğer kişiler için bağlama göre “dedi”, “şöyle dedi”, “anlattı” veya “rivayet etti” kullanılır.

## Türkçe Üslup

- Türkiye’de yayımlanan nitelikli hadis tercümelerindeki yerleşik ifadeler tercih edilir.
- Metin ne aşırı modernleştirilir ne de anlaşılmaz Osmanlıca ile ağırlaştırılır.
- Arapça cümle dizimi Türkçeye taşınmaz.
- Kelime kelime çeviri hissi veren ifadeler kullanılmaz.
- Türkçe cümleler doğal, temiz ve tek başına anlaşılır olmalıdır.
- Gereksiz tekrar, bozuk tamlama ve düşük anlatım bırakılmaz.
- Diyaloglar okunaklı biçimde kurulur.
- Metinde olmayan “kâmil mânada”, “yani”, “başka bir ifadeyle” gibi açıklayıcı ekler yapılmaz.

## Terim ve Yazım Standardı

- `صلى الله عليه وسلم` → `(s.a.v.)`
- `رضي الله عنه` → `(r.a.)`
- `رضي الله عنها` → `(r.anha)`
- `رضي الله عنهما` → `(r.anhuma)`
- `رضي الله عنهم` → `(r.anhum)`
- Hz. Peygamber için bağlama göre “Resûlullah (s.a.v.)” veya “Nebî (s.a.v.)” kullanılır.
- Kişi adlarında tutarlı biçimde `b.` kullanılır: “Abdullah b. Amr”.
- Yaygın yazımlar korunur:
  - Âişe
  - İbn Abbâs
  - Ebû Hüreyre
  - Enes
  - Cebrâil
  - Resûlullah
  - Nebî
  - Kur’an
  - İslâm
  - mümin
  - sahâbî
- `يا رسول الله` → “Yâ Resûlallah!”
- `يا نبي الله` → “Yâ Nebiyyallah!”
- `فوالذي نفسي بيده` ve benzeri yeminler bağlama göre “Canım elinde olan Allah’a yemin ederim ki” şeklinde aktarılır.
- Üstünlük bildiren yapılar zayıflatılmaz:
  - “en cömert”
  - “en ağır”
  - “en faziletli”
  - “daha sevgili”

## Kalite Kontrol

Codex çeviri dosyalarını yazdıktan sonra şu kontrolleri yapmalıdır:

1. Dosya geçerli JSON mu?
2. JSON yalnızca `tr`, `reference`, `grade` alanlarını mı içeriyor?
3. `reference` kaynakla birebir aynı mı?
4. Kaynak metindeki bütün anlam birimleri Türkçede var mı?
5. Konuşmacılar doğru mu?
6. Zamirler doğru kişilere bağlanıyor mu?
7. Olumsuzluklar, yeminler ve üstünlük dereceleri korunmuş mu?
8. Kaynakta olmayan açıklama veya yorum eklenmiş mi?
9. Türkçe doğal ve yayıma uygun mu?
10. Kişi adları, dua kısaltmaları ve terimler tutarlı mı?

Kontroller sırasında tespit edilen tüm çeviri ve biçim sorunlarını dosyalarda doğrudan düzelt, ardından kontrolleri yeniden çalıştır.

Örnek doğrulama:

```bash
for f in translations/bukhari/{1..20}.json; do
  jq empty "$f" || exit 1
done
```

## Raporlama

Görev sonunda kısa rapor ver:

- Hangi kaynak dosya kullanıldı?
- Hangi hadis aralığı işlendi?
- Hangi dosyalar zaten mevcut olduğu için atlandı?
- Hangi dosyalar yeni oluşturuldu?
- JSON ve reference kontrolleri geçti mi?
- Herhangi bir hadis için tereddüt veya risk var mı?
