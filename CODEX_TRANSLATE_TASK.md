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
  "reference": "<kaynak reference değeri>"
}
```


## Çeviri Kuralları

Temel ilke: Bu görev lafzî Arapça aktarımı değil, Türkiye'deki klasik hadis tercüme geleneğine uygun bir Türkçe hadis tercümesi üretme görevidir.

- Diyanet hadis tercümeleri, Riyâzü's-Sâlihîn tercümeleri ve klasik Buhari-Müslim tercüme üslubunda yerleşmiş dil ve terminolojiyi esas al.
- Bir ifade için Arapça lafza yakın karşılık ile yerleşik hadis tercümesi karşılığı arasında tercih gerekiyorsa yerleşik karşılığı kullan.
- Modernleştirme, gereksiz sadeleştirme, akademik üslup veya özgün karşılık üretme yoluna gitme.
- Arapça veya Osmanlıca kökenli bir kelimeyi yalnızca Türkçedeki hadis tercümelerinde yaygın ve doğal ise kullan.
- Türkçede yerleşmiş hadis kalıplarını koru; Türkçede doğal olmayan kelime sıralamalarını düzeltirken anlamdan uzaklaşma.
- Metinden anlam eksiltme veya metne yorum yoluyla anlam ekleme.
- Hadisin manevî ve edebî üslubunu koru.
- Birden fazla anlam ihtimali varsa hadis tercüme geleneğinde en güçlü olan anlamı seç; JSON içine açıklama, dipnot veya ihtimal notu ekleme.
- Okuyucunun bilmeyebileceği kişi, yer, kabile, olay ve kavramlar aynı hadis metni içinde ilk geçtiği yerde en az kelimeyle kısa biçimde tanıtılabilir; sonraki tekrarlarında açıklama yeniden verilmez.
- Yalnızca metnin anlaşılması için zorunlu, kısa ve kesin tarihî bağlam bilgileri doğal biçimde eklenebilir; yorum, tahmin ve ihtilaflı açıklama eklenmez.
- Klasik hadis/siyer terimleri Türkçede aynen kullanılacaksa ve ortalama Türk okuyucu için anlamı açık değilse aynı hadis içinde ilk geçtiği yerde kısa açıklama ver.
- Kaynak `english` alanındaki parantez açıklamaları otomatik olarak Türkçeye taşıma; yalnızca Türk okuyucu için gerçekten gerekli ve kısa olanları kullan.
- Kaynakta sûre/âyet kimliği, Kur'an referansı veya hadiste kısmen zikredilen sûre lafzını tanımayı kolaylaştıran bilgi varsa bunu kısa ve doğal biçimde Türkçeye taşı.

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
