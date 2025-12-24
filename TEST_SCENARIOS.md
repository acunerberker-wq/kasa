# Satın Alma Sipariş Raporları - Test Senaryoları

## 1) Açık satın alma siparişleri (tedarikçi bazlı)
1. En az iki tedarikçiye ait açık sipariş oluşturun (durum: oluşturuldu/onaylandı/kısmi teslim alındı).
2. Her sipariş için en az bir kalem girin, farklı para birimi ve kur bilgisi ekleyin.
3. Raporu çalıştırın ve tedarikçi + para birimi bazında toplamların listelendiğini doğrulayın.
4. İptal ve teslim alındı durumundaki siparişlerin listede görünmediğini kontrol edin.

## 2) Teslim alma performansı
1. Teslim tarihi dolmuş ve teslim alınmış sipariş oluşturun.
2. Aynı siparişe kısmi teslim kaydı girin.
3. Raporu çalıştırın; gecikme gününün pozitif çıktığını, kısmi teslim sütununun “Evet” olduğunu doğrulayın.
4. Teslim tarihi olmayan siparişlerde gecikme sütununun boş olduğunu kontrol edin.

## 3) Beklenen maliyet (açık PO toplamı)
1. Açık siparişlerde iskonto oranı ve kur bilgisi ekleyin.
2. Kısmi teslim girerek kalan tutarı düşürün.
3. Raporu çalıştırın; açık tutar, kur ve TL karşılığının beklenen maliyetle eşleştiğini doğrulayın.

## 4) Mal kabul → fatura eşleşme kontrolü
1. Teslim kaydı oluşturun; fatura eşlemesi olmayan teslimleri ekleyin.
2. Bir teslimi faturaya bağlayın.
3. Raporu çalıştırın; eşleşen teslimlerde “Eşleşti”, eksiklerde “Eksik” göründüğünü doğrulayın.

## 5) Filtreler
1. Tedarikçi, ürün, durum, tarih, depo filtrelerini sırayla uygulayın.
2. Her filtre değişiminde rapor sonuçlarının daraldığını doğrulayın.
3. Şirket etiketi, aktif şirket adını göstermelidir.

## 6) Export / Yazdırma
1. Her raporda CSV export alın; dosyada başlık ve satırların doğru sırada olduğunu doğrulayın.
2. openpyxl mevcutsa Excel export alın; sütun genişliklerini kontrol edin.
3. reportlab mevcutsa PDF export alın; başlık ve tablo çıktısının yazdırmaya uygun olduğunu doğrulayın.
