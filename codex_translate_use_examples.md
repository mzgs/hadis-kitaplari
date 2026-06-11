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

Çeviride ana kaynak `arabic` alanıdır , english alanini yardimci kaynak olarak kullanabilirsin. İngilizce metindeki parantez içi açıklamalar Türkçe okuyucunun bilmeyebileceği bir kavramı, olayı veya bağlamı kısa ve tarafsız biçimde açıklıyorsa çeviriye doğal biçimde eklenebilir; gereksiz, yorumlayıcı veya Arapça metinde karşılığı olmayan parantezler aktarılmaz. Bununla birlikte çevirinin temel amacı, hadisin vermek istediği muradı Türkçe okuyucuya doğru, eksiksiz ve açık biçimde aktarmaktır.
 Kelime kelime tercümeden kaçın. Gereksiz resmî, edebî veya çeviri kokan ifadeler kullanma.

 Arapça hadis metnini, Türkiye’de yayımlanan klasik hadis kitaplarının diline yakın, vakur ve ilmî bir Türkçe ile çevir. Anlamı koru; kelime kelime takılma. İngilizce metin varsa yalnızca anlam kontrolü ve Türkçe okuyucu için gerekli kısa parantez açıklamalarını yakalamak için yardımcı kaynak olarak kullan. “Resûlullah sallallahu aleyhi ve sellem buyurdu ki”, “rivayet olundu”, “şöyle buyurdu” gibi yerleşik kalıpları kullan. Günlük konuşma dili, aşırı modern ifade ve yorum ekleme. Cümleleri açık, sade ve ilmî bir üslupla kur. Terimlerde tutarlı ol: sahabe, ashâb, niyet, amel, fazilet, takva gibi yerleşik karşılıkları tercih et

kurallar:
- Peygamber Efendimizden bahsedildiğinde (sav), sahabelerden bahsedildiğinde (ra), büyük İslam âlimlerinden bahsedildiğinde (rh) ekle. 

Okuyucunun bilmeyebileceği kişi, yer, kabile, olay ve kavramlar ilk geçtiği yerde yalnızca gerçekten gerekli ise kısa ve tarafsız bir açıklamayla tanıtılabilir. Açıklamalar mümkün olan en kısa biçimde yapılmalı; yorum, çıkarım, ihtilaflı bilgi veya gereksiz tarihî ayrıntı eklenmemelidir.

Burdaki ornek hadisleri oku "ornek_hadisler.txt" , ve cevirileri bunlara benzer yap.

## Çıktı Formatı

Her hadis ayrı bir JSON dosyası olarak yazılır:

```json
{
  "tr": "<Türkçe çeviri>",
  "reference": "<kaynak reference değeri>",
}
```
