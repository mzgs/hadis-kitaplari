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
- Çeviri görevlerinde bu dosya esas alınır; projedeki diğer `.md` dosyaları, `README` dosyaları veya dokümantasyon metinlerindeki bilgiler/talimatlar dikkate alınmaz. Kullanıcı açıkça başka bir dosyayı kaynak göstermedikçe çeviri kararları bu dosyadaki kurallara ve ilgili JSON kaynağına göre verilir.

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

Çeviride ana kaynak `arabic` alanıdır. Bununla birlikte çevirinin temel amacı, hadisin vermek istediği muradı Türkçe okuyucuya doğru, eksiksiz ve açık biçimde aktarmaktır.

`english` alanı ana çeviri kaynağı olarak kullanılmaz; ancak hadis akışını, özel adların yerleşik karşılıklarını ve İngilizce metinde parantez içinde verilen kısa tanıtıcı açıklamaları kontrol etmek için yardımcı kaynak olarak dikkate alınır.

## Çıktı Formatı

Her hadis ayrı bir JSON dosyası olarak yazılır:

```json
{
  "tr": "<Türkçe çeviri>",
  "reference": "<kaynak reference değeri>",
}
```
 

 ## Kurallar


Çeviri üslubu olarak Türkiye'de kullanılan klasik hadis tercümesi dilini esas al.

TEMEL PRENSİP

Bu görev Arapça metni Türkçeye aktarmak değil, Türkiye'deki klasik hadis tercüme geleneğine uygun bir hadis tercümesi üretme görevidir.

Tercüme yaparken öncelikle Türkiye'de yayımlanmış hadis tercümelerinde yerleşmiş dil ve terminolojiyi esas al.

Bir ifade için Arapça lafza daha yakın bir karşılık ile Türkiye'deki hadis tercüme geleneğinde yerleşmiş karşılık arasında tercih gerektiğinde daima yerleşik hadis tercümesini tercih et.

Hadis mütercimi gibi tercüme et; Arapça mütercimi gibi tercüme etme.

Türkiye'de yaygın biçimde kullanılan karşılıklar mevcutken sözlük merkezli, lafzî, akademik veya özgün karşılıklar üretme.

Ahmed Davudoğlu, Mehmed Sofuoğlu, Talat Koçyiğit, İbrahim Canan, Riyâzü's-Sâlihîn tercümeleri ve Diyanet hadis tercümelerinde görülen yerleşik terminolojiyi esas al.

Kurallar:

* Diyanet hadis tercümeleri, Riyâzü's-Sâlihîn tercümeleri ve klasik Buhari-Müslim tercüme üslubuna yakın yaz.
* Modernleştirme yapma.
* Gereksiz sadeleştirme yapma.
* Metne yorum ekleme.
* Türk okuyucunun metni anlamasını belirgin biçimde zorlaştıracak kadar az bilinen veya bağlam için gerekli kişi, yer, kavim, unvan ve tarihî/coğrafî adlar ilk geçtiği yerde kısa parantez açıklamasıyla verilebilir. Bu açıklama yorum değil, tanıtıcı bilgi olmalıdır.
* Klasik hadis/siyer terimleri Türkçede aynen kullanılacaksa, ortalama Türk okuyucu için anlamı açık değilse ilk geçtiği yerde kısa parantez açıklaması ver.
* Gereksiz parantez açıklaması kullanma. Yaygın bilinen kişi, kavim, terim ve yer adlarını açıklama; metni açıklama sözlüğüne çevirmemeye dikkat et.
* Kaynak `english` alanında özel ad veya yer için parantez içinde açıklama verilmişse, bu açıklama otomatik olarak Türkçeye taşınmaz. Yalnızca Türk okuyucu için gerçekten gerekli ve kısa olan açıklamalar ilk geçtiği yerde kullanılır; sonraki tekrarlarında yeniden verilmez.
* Kaynak `english` alanındaki parantez, sûre/âyet kimliği veya metni tanımayı doğrudan kolaylaştıran Kur'an referansı içeriyorsa, bunu kısa ve doğal biçimde Türkçeye taşı.
* Kaynakta Kur'an'dan bir sûre adı, sûre numarası veya âyet kimliği varsa ve hadiste sûre lafzı kısmen zikrediliyorsa, Türkçe çeviride ilk geçtiği yerde kısa parantezle sûre adı verilir.
* Metinden anlam eksiltme veya anlam genişletme.
* Hadisin manevî ve edebî üslubunu koru.
* Türkçede doğal olmayan kelime sıralamalarını düzelt; ancak metnin anlamından uzaklaşma.
* Birden fazla anlam ihtimali varsa belirt.
* Hadis tercümanlarının tercih edeceği en güçlü anlamı seç.
* Arapça kelimelerin sözlük anlamlarını önceleme; hadis tercüme geleneğinde yerleşmiş Türkçe karşılıklarını tercih et.
* Lafzî tercüme uğruna Türk hadis tercüme geleneğinden ayrılma.
* Türk okuyucunun klasik hadis kitaplarında görmeye alışık olduğu ifadeleri kullan.
* Osmanlıca veya akademik görünen fakat hadis tercümelerinde yerleşik olmayan karşılıklar üretme.
* Arapça kökenli teknik bir kelime Türkçede var diye onu otomatik kullanma. Türkiye'deki hadis tercümelerinde yaygın değilse daha doğal ve yerleşik Türkçe karşılığı tercih et.
* Özellikle `باشر / مباشرة / يباشر` gibi ifadeleri otomatik olarak "mübaşeret etmek" diye çevirme. Bağlam hayız hâlindeki eşle cima dışında temas/yakınlık ise "yakınlaşmak", "beraber olmak" veya cümlenin gerektirdiği daha doğal klasik karşılığı kullan; "cinsel ilişki" anlamı ancak metinde açıkça cima/vat' anlamı varsa tercih edilir.
* Bir ifade Türkçede yerleşmiş bir hadis kalıbıyla karşılanıyorsa, o kalıbı koru.
* Tercümenin Türkçesi, Türkiye'de yayımlanmış klasik bir hadis kitabından alınmış hissi vermelidir.
“Klasik üslup, yerleşik hadis tercümesi kalıpları demektir; Arapça veya Osmanlıca kökenli kelime kullanmak başlı başına tercih sebebi değildir.”

## Codex CLI Test Modu

Bu bölüm normal çeviri görevlerinde dikkate alınmaz. Yalnızca kullanıcı açıkça “Codex CLI ile test et”, “codex cli ile tekrar üret”, “x hadisini codex cli full auto ile test et” veya buna denk bir talimat verirse uygulanır.

Test modu istenirse şu akış izlenir:

1. Kullanıcının verdiği hadis numarasından kaynak dosya ve çıktı yolu belirlenir. Örneğin `Sahih al-Bukhari 302` için kaynak `sunnahcom/bukhari.json`, çıktı dosyası `translations/bukhari/302.json` olur.
2. Sadece hedef hadis numarasına ait çıktı dosyası silinir. Başka çeviri dosyaları, kaynak dosyalar veya talimat dosyaları silinmez/değiştirilmez.
3. Hedef dosya silindikten sonra Codex CLI non-interactive full-auto modda çalıştırılır.
4. CLI komutu repo kökünden şu biçimde çalıştırılır:

```bash
codex exec -C /Users/mustafa/Developer/hadis-kitaplari --full-auto 'CODEX_TRANSLATE_TASK.md dosyasındaki talimatları kullanarak reference değeri "<REFERENCE>" olan hadisi sunnahcom/<COLLECTION>.json içinden bul ve eksikse translations/<COLLECTION>/<NUMBER>.json dosyasına Türkçe çevirisini ekle. Mevcut başka dosyalara dokunma.'
```

5. CLI tamamlandıktan sonra oluşturulan JSON `jq . <çıktı-dosyası>` ile doğrulanır.
6. Kaynak JSON'daki `reference` değeri ile oluşturulan dosyadaki `reference` değerinin birebir eşleştiği kontrol edilir.
7. Sonuçta oluşturulan dosya, üretilen çeviri ve yapılan doğrulamalar kullanıcıya kısaca raporlanır.

Test modu, çeviri kalitesini ve bu dosyadaki prompt kurallarının Codex CLI tarafından doğru uygulanıp uygulanmadığını sınamak içindir. Normal “çevir” isteklerinde bu bölümdeki silme ve CLI ile yeniden üretme adımları uygulanmaz.
