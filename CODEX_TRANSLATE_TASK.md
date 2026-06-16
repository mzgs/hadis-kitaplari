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
 

## Çıktı Formatı

Her hadis ayrı bir JSON dosyası olarak yazılır:

```json
{
  "tr": "<Türkçe çeviri>",
  "reference": "<kaynak reference değeri>"
}
```


## Çeviri Kuralları
Aşağıdaki klasik Arapça metni Türkçeye çevir. Google Translate tarzı kelime kelime çeviri yapma. Klasik Arapça, hadis ve fıkıh terminolojisini dikkate alarak akıcı ve doğru bir tercüme yap. Özel terimleri bağlama göre anlamlandır, gerekmedikçe açıklama ekleme.

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
