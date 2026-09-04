# Hadis Düzeltme İlerlemesi

## Görev

`fromdoc/tur-bukhari.json` dosyasındaki hadisleri referans numarasına göre 1'den başlayarak sırayla incele ve düzelt. Bu dosya daha sonraki oturumlarda görevin kaldığı yerden anlaşılması için kalıcı çalışma talimatıdır.

## Çalışma Kuralları

1. Önce bu dosyayı ve `buhari-logs.md` dosyasını oku.
2. `Son tamamlanan hadis` değerinden sonraki referansla devam et.
3. Her hadiste Arapça ile Türkçenin aynı rivayete ait olduğunu kontrol et.
4. Türkçedeki OCR hatalarını, bozuk karakterleri, yarım ifadeleri ve gereksiz kaynak artıklarını düzelt.
5. `BURAYA TIKLAYIN`, tek başına kalan `Tekrar:`, bozuk sayfa numarası, gereksiz dipnot rakamı ve benzeri artıklar temizlenmelidir.
6. Türkçe alandaki uzun açıklama veya şerh, açıkça bozuk ya da başka hadise ait değilse korunabilir.
7. Arapça alan eksik veya kesilmişse öncelikle `arabic_books/collections/bukhari.json`, gerekirse diğer güvenilir yerel Buhari kaynakları kullanılarak tamamlanmalıdır.
8. Metnin anlamını keyfi biçimde modernleştirme; yalnız doğrulanabilir düzeltmeler yap.
9. Her değişikliği `buhari-logs.md` dosyasına referans, alan, gerekçe, eski parça ve yeni parça olarak ekle. Alanın tamamı değiştirilmediyse hadisin tam metnini yazma; yalnız değiştirilen kelimeyi, cümleyi veya bölümü kaydet.
10. Her çalışma görevinde sıradaki tam 5 hadisi incele (örneğin 21-25, ardından 26-30). Kullanıcı açıkça farklı bir sayı istemedikçe bir görevde 5 hadisten fazla ilerleme.
11. Her 5 hadislik çalışma grubundan sonra JSON ayrıştırmasını, referans sırasını ve değiştirilen kayıtları doğrula.
12. Doğrulama tamamlandıktan sonra bu dosyadaki ilerleme bilgilerini güncelle.

## İlerleme

- Koleksiyon: Sahih al Bukhari
- Hedef dosya: `fromdoc/tur-bukhari.json`
- Başlangıç: Sahih al Bukhari 1
- Son tamamlanan hadis: Sahih al Bukhari 20
- Sonraki hadis: Sahih al Bukhari 21
- Son çalışma tarihi: 2026-09-04
- Durum: Devam ediyor
- Çalışma grubu boyutu: 5 hadis

## Devam Komutu

Kullanıcı `progress dosyasından devam et`, `Buhari düzeltmesine devam et` veya benzeri bir ifade kullandığında bu talimatlara göre yalnızca sıradaki 5 hadisi, yani Sahih al Bukhari 21-25 arasını incele. Sonraki görevde 26-30 aralığıyla devam et.
