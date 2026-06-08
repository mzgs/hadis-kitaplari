# Hadis Çeviri Terimlerini Kontrol ve Güncelleme Görevi

Bu dosya çalıştırıldığında mevcut hadis çevirilerini kaynak Arapça metinlerle
karşılaştır ve `translate_chatgpt_web.py` içindeki:

> Aşağıdaki ifadeler geçtiğinde şu karşılıkları kullan:

alanını güncelle.

## Varsayılan Dosyalar

- Arapça kaynak: `sunnahcom/bukhari.json`
- Türkçe çeviriler: `translations/bukhari/*.json`
- Güncellenecek dosya: `translate_chatgpt_web.py`

Kullanıcı başka bir hadis kitabı veya çeviri klasörü belirtirse aynı işlemi
belirtilen dosyalara uygula.

## Amaç

Mevcut Türkçe çevirilerde:

- Arapça cümle yapısının Türkçeye yapay biçimde taşındığı,
- kelime kelime çevrildiği,
- anlamın zayıflatıldığı veya yanlış yönlendirildiği,
- Türkiye Türkçesinde daha doğal ve yerleşik bir karşılığı bulunan,
- başka hadislerde de tekrar kullanılabilecek

Arapça kelime ve kısa ifadeleri tespit et.

Tespit edilen uygun karşılıkları `translate_chatgpt_web.py` içindeki mevcut
karşılık listesine ekle veya listedeki sorunlu karşılıkları düzelt.

## İnceleme Yöntemi

1. Kaynak JSON'daki bütün hadisleri `books[*].content[*]` sırasıyla birleştir.
2. `translations/bukhari/` içindeki numaralı JSON dosyalarını aynı 1 tabanlı
   indeksle kaynak hadislerle eşleştir.
3. Her çevirideki `tr` alanını öncelikle kaynak hadisin `arabic` alanıyla
   karşılaştır.
4. `english` alanını yalnızca anlam ve bağlam kontrolünde yardımcı kaynak
   olarak kullan; İngilizceyi esas alma.
5. Doğal görünmeyen Türkçe ifadelerin kaynak Arapça karşılığını belirle.
6. Aynı Arapça kalıbın kaynakta başka nerelerde geçtiğini kontrol ederek
   önerilen Türkçe karşılığın tekrar kullanılabilir olduğundan emin ol.
7. Mevcut karşılık listesini okuyarak aynı veya çelişen bir madde ekleme.

## Eklenecek Maddelerin Biçimi

Maddeleri şu biçimde yaz:

```text
* <Arapça kelime veya kısa ifade> → <doğal Türkçe karşılık>
```

Tercih sırası:

1. Kısa ve farklı hadislerde tekrar kullanılabilir ifade
2. Türkiye'de yerleşik hadis tercümesi karşılığı
3. Anlamı ve vurgu derecesini koruyan doğal Türkçe
4. Gerektiği kadar bağlam içeren, ancak tam hadis cümlesi olmayan kalıp

Örnek:

```text
* سلم من لسانه ويده → dilinden ve elinden emin olmak
* يفقهه في الدين → dinde fakih kılmak
* لا حسد إلا → ancak ... gıpta edilir
* الحرص على الحديث → hadis öğrenme gayreti
```

## Kaçınılacak Maddeler

- Yalnızca tek bir hadise yarayacak uzun ve tam cümleler ekleme.
- Salavat, sahâbe duası, kişi adı yazımı ve benzeri genel yazım standartlarını
  bu alana ekleme.
- Zaten doğal ve doğru çevrilen ifadeleri sırf sık geçtiği için ekleme.
- Çok anlamlı bir Arapça kelimeyi tek başına kesin bir Türkçe karşılığa
  bağlama.
- Bağlama göre farklı anlamlara gelen `ألا`, `عرض`, `كره` gibi kelimeleri
  yeterli bağlam olmadan ekleme.
- İngilizce çevirideki bir tercihi Arapça metni doğrulamadan kullanma.
- Aynı anlamı veren mükerrer veya birbiriyle çelişen maddeler oluşturma.

Çok anlamlı bir kelime için kısa fakat ayırt edici bir kalıp kullan:

```text
* لدينه وعرضه → dinini ve namusunu
* يكره أن يعود في الكفر → küfre dönmeyi kötü görmek
* ألا وإن / ألا إن → Dikkat edin!
```

## Düzenleme Sınırları

- Normal çalışmada yalnızca `translate_chatgpt_web.py` içindeki karşılık
  listesini güncelle.
- Mevcut `translations/bukhari/*.json` çevirilerini değiştirme.
- Kullanıcı açıkça istemedikçe promptun diğer kurallarını, Python kodunu veya
  başka dosyaları değiştirme.
- Kullanıcının çalışma alanındaki ilgisiz değişikliklere dokunma.
- Mevcut doğru maddeleri koru; yalnızca hatalı, fazla geniş, fazla uzun veya
  mükerrer olanları düzelt.

## Kalite Kontrol

Güncellemeden sonra:

1. Eklenen her Arapça ifadenin kaynak JSON'da gerçekten geçtiğini doğrula.
2. İfadenin başka bağlamlarda yanlış sonuç üretmeyecek kadar belirgin
   olduğundan emin ol.
3. Uzun maddeleri mümkünse daha kısa, anlamlı parçalara böl.
4. Çok kısa ve çok anlamlı maddeleri yeterli bağlamla sınırla.
5. Listenin mükerrer veya çelişkili madde içermediğini kontrol et.
6. Python dosyasını dosya üretmeden sözdizimi kontrolünden geçir:

```bash
python3 - <<'PY'
from pathlib import Path

path = Path("translate_chatgpt_web.py")
compile(path.read_text(encoding="utf-8"), str(path), "exec")
print("syntax ok")
PY
```

7. Biçim sorunlarını kontrol et:

```bash
git diff --check
```

## Raporlama

İşlem sonunda kısa biçimde şunları bildir:

- Hangi kaynak ve çeviri klasörünün incelendiği
- Kaç yeni kısa ifade eklendiği
- Kaç mevcut maddenin daraltıldığı, düzeltildiği veya kaldırıldığı
- Sözdizimi ve diff kontrollerinin sonucu

