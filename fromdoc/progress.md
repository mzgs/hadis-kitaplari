# Hadis Düzeltme İlerlemesi

## Görev

Bu klasördeki `tur-bukhari.json` dosyasında bulunan hadisleri referans numarasına göre 1'den başlayarak sırayla incele ve düzelt. Bu dosya daha sonraki oturumlarda görevin kaldığı yerden anlaşılması için kalıcı çalışma talimatıdır. Çalışma klasörü bağımsızdır; üst klasördeki veya başka yerlerdeki dosyalara bağımlı olma.

## Çalışma Kuralları

1. Önce bu dosyayı ve `buhari-logs.md` dosyasını oku.
2. `Son tamamlanan hadis` değerinden sonraki referansla devam et.
3. Her hadiste Arapça ile Türkçenin aynı rivayete ait olduğunu kontrol et.
4. Türkçedeki OCR hatalarını, bozuk karakterleri, yarım ifadeleri ve gereksiz kaynak artıklarını düzelt.
5. `BURAYA TIKLAYIN`, tek başına kalan `Tekrar:`, bozuk sayfa numarası, gereksiz dipnot rakamı ve benzeri artıklar temizlenmelidir.
6. Türkçe alandaki uzun açıklama veya şerh, açıkça bozuk ya da başka hadise ait değilse korunabilir.
7. Arapça alan eksik, kesilmiş veya şüpheliyse yerel kaynak arama; gerektiğinde internetten güvenilir Buhari kaynaklarını araştırarak doğrula ve tamamla. Kaynaklar çelişirse birden fazla güvenilir çevrim içi kaynağı karşılaştır.
8. Metnin anlamını keyfi biçimde modernleştirme; yalnız doğrulanabilir düzeltmeler yap.
9. Her değişikliği `buhari-logs.md` dosyasına referans, alan, gerekçe, eski parça ve yeni parça olarak ekle. İnternet araştırması kullanıldıysa doğrulama kaynağının bağlantısını da kaydet. Alanın tamamı değiştirilmediyse hadisin tam metnini yazma; yalnız değiştirilen kelimeyi, cümleyi veya bölümü kaydet.
10. Her çalışma görevinde sıradaki tam 5 hadisi incele (örneğin 21-25, ardından 26-30). Kullanıcı açıkça farklı bir sayı istemedikçe bir görevde 5 hadisten fazla ilerleme.
11. Her 5 hadislik çalışma grubundan sonra JSON ayrıştırmasını, referans sırasını ve değiştirilen kayıtları doğrula.
12. Doğrulama tamamlandıktan sonra bu dosyadaki ilerleme bilgilerini güncelle.

## İlerleme

- Koleksiyon: Sahih al Bukhari
- Hedef dosya: `tur-bukhari.json`
- Başlangıç: Sahih al Bukhari 1
- Son tamamlanan hadis: Sahih al Bukhari 30
- Sonraki hadis: Sahih al Bukhari 31
- Son çalışma tarihi: 2026-09-04
- Durum: Devam ediyor
- Çalışma grubu boyutu: 5 hadis

## Devam Komutu

Kullanıcı `progress dosyasından devam et`, `Buhari düzeltmesine devam et` veya benzeri bir ifade kullandığında bu talimatlara göre yalnızca sıradaki 5 hadisi, yani Sahih al Bukhari 31-35 arasını incele. Sonraki görevde 36-40 aralığıyla devam et.
