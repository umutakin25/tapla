# PowerShell Komut Listesi

> Her PowerShell açtığında İLK komut bu. Satır başında `PS C:\Projeler\yorumrapor>`
> yazmıyorsa yanlış yerdesin, komutlar çalışmaz.
>
> ```powershell
> cd C:\Projeler\yorumrapor
> ```

---

## RAPOR

**Yeni işletme raporu (veya aylık takip — aynı komut):**
```powershell
.\venv\Scripts\python.exe main.py "İşletme Adı" "GOOGLE_MAPS_LINKI"
```
- İlk çalıştırma: tüm yorumları tarar
- Sonraki aylar: sadece yeni yorumları analiz eder, geçen dönemle kıyaslar
- **İşletme adını her seferinde birebir aynı yaz**, yoksa hafıza tutmaz

**Raporu aç:**
```powershell
start isletme_adi_rapor.html
```
Sonra tarayıcıda `Ctrl+P` → "PDF olarak kaydet"

**Apify'a gitmeden raporu yeniden üret** (şablon değişince işe yarar):
```powershell
.\venv\Scripts\python.exe -c "import json; from report import render_report; a=json.load(open('SLUG_analiz.json',encoding='utf-8')); render_report('İşletme Adı', a, 62, 'SLUG_rapor.html')"
```

---

## KARTLAR

**Yeni kart kodu üret (10 tane):**
```powershell
.\venv\Scripts\python.exe kart_yonet.py uret 10
```

**Kartı işletmeye ata (satış anında):**
```powershell
.\venv\Scripts\python.exe kart_yonet.py ata KOD "İşletme Adı" "YORUM_LINKI"
```
Aynı komutu tekrar çalıştırırsan hedefi değiştirirsin (karta dokunmadan).

**Okutma istatistiği:**
```powershell
.\venv\Scripts\python.exe kart_yonet.py stat KOD
```

**Tüm kartları listele:**
```powershell
.\venv\Scripts\python.exe kart_yonet.py liste
```

---

## DOSYA / KLASÖR

**Klasördeki dosyaları gör:**
```powershell
dir
```

**Ayar dosyasını aç (API anahtarları):**
```powershell
notepad .env
```

**Kart listesini aç:**
```powershell
notepad kartlar.csv
```

**Yeni sürüm zip'ini kur (üzerine yazar, venv ve .env korunur):**
```powershell
Expand-Archive -Path "$HOME\Downloads\ZIPADI.zip" -DestinationPath "C:\Projeler" -Force
```

**Tek dosyayı üzerine kopyala:**
```powershell
copy "$HOME\Downloads\dosya.html" "templates\rapor.html" -Force
```

---

## SORUN GİDERME

**Kütüphaneleri yeniden kur:**
```powershell
.\venv\Scripts\pip.exe install -r requirements.txt
```

**Python sürümünü gör:**
```powershell
py --version
```

**Bir dosyada metin ara:**
```powershell
Select-String -Path templates\rapor.html -Pattern "aradığın-kelime"
```

---

## DİKKAT

- Proje dosyalarını `Get-Content` / `Set-Content` ile değiştirme — Türkçe karakterleri bozar. Not Defteri kullan.
- `data\` klasörünü silme — aylık takip hafızası orada.
- `kartlar.csv` dosyasını silme — hangi kod hangi işletmede bilgisi orada. Yedekle.
- Google Maps linkini komutta **tırnak içine al**, yoksa `&` karakteri komutu böler.
