# Sorun Giderme

Yaşanmış hatalar ve çözümleri.

## Panele okutma düşmüyor

**Belirti:** Kart okutuluyor, Google sayfası açılıyor ama panelde sayaç artmıyor.

**Sebep:** Kartın `token` alanı silinmiş. v8 öncesinde `ata` komutu kart
kaydını yeniden yazarken token'ı siliyordu.

**Çözüm:**
```powershell
python panel_yonet.py ac "İŞLETME ADI"
```
Çıktıda `N kayip okutma kurtarildi` görürsen kayıp okutmalar geri geldi.

**Doğrulama:**
```powershell
$key = (Get-Content .env | Select-String 'ADMIN_KEY=').ToString().Split('=')[1].Trim()
Invoke-RestMethod "https://taplatr.com/api/stat/KOD?key=$key" | ConvertTo-Json
```
Çıktıda `token` alanı olmalı.

---

## Panel güncellenmiyor / eski veri gösteriyor

**Sebep:** Service worker önbelleği.

**Çözüm:**
- Telefonda: uygulamayı kapat-aç
- Bilgisayarda: `Ctrl+Shift+R`
- Panelin altındaki sürüm numarasına bak, güncel mi?

---

## "Bu bağlantı geçersiz"

Panel KV'ye yazılmamış.

```powershell
# 1) Worker sürümü
(Invoke-WebRequest "https://taplatr.com/p/sw.js" -UseBasicParsing).Content | Select-String 'tapla-v\d+'

# 2) Yönetim ucu çalışıyor mu ("yetkisiz" dönerse OK)
Invoke-WebRequest "https://taplatr.com/api/isletme" -UseBasicParsing

# 3) Paneli tekrar aç
python panel_yonet.py ac "İŞLETME ADI"
```

---

## Komut çalıştırınca site HTML'i akıyor

**Sebep:** Yönetim ucu `/api/` öneki olmadan çağrılıyor, istek Pages'e gidiyor.

**Çözüm:** Python dosyalarını güncelle (v8+), worker'ı deploy et.

---

## Kart haritayı açıyor, yorum ekranını açmıyor

**Sebep:** Hedef maps linki olmuş.

**Çözüm:** `search.google.com/local/writereview?placeid=...` linkiyle yeniden ata.

---

## `ModuleNotFoundError: No module named 'requests'`

Sistem Python'u kullanılmış.

```powershell
.\venv\Scripts\python.exe komut.py
```

---

## `KeyError: 'kod'`

**Sebep:** PowerShell `Export-Csv` dosyanın başına `#TYPE` satırı eklemiş.

```powershell
.\venv\Scripts\python.exe -c "import csv; s=[l for l in open('kartlar.csv',encoding='utf-8-sig') if l.strip() and not l.startswith('#TYPE')]; open('kartlar.csv','w',encoding='utf-8',newline='').writelines(s); print('temizlendi')"
```

CSV'ye elle dokunma, komutları kullan.

---

## Dosya kopyalanmıyor (hata da vermiyor)

**Sebep:** Dosya açık/kilitli (VS Code, çalışan Python).

```powershell
Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force
Remove-Item dosya.py -Force
Copy-Item "kaynak\dosya.py" . -Force
Select-String -Path dosya.py -Pattern "beklenen_satir"
```

Son satır doğrulama — atlama.

---

## `.pages.dev` açılmıyor

Türkiye'de bazı operatörler bu uzantıyı engelliyor. DNS yanlış IP dönüyor.

**Çözüm:** DNS'i `1.1.1.1` yap ya da kendi domainini kullan.
Ziyaretçiler etkilenmez, sadece senin bağlantında sorun var.

---

## Deploy kontrolü

```powershell
# Canlıdaki sürüm
(Invoke-WebRequest "https://taplatr.com/p/sw.js" -UseBasicParsing).Content | Select-String 'tapla-v\d+'

# Yerel dosyadaki sürüm
Select-String -Path worker.js -Pattern 'SURUM = "v'
```

İkisi aynı değilse deploy tamamlanmamış. Cloudflare → `taplink` → Deployments
sekmesinden son deploy zamanını kontrol et.
