# Sıfırdan Kurulum

## 1. Hesaplar

| Servis | Ne için | Plan |
|---|---|---|
| [Cloudflare](https://cloudflare.com) | Worker + KV + Pages | Ücretsiz |
| [Apify](https://apify.com) | Google yorum çekme | Ücretli (kullanım başına) |
| [Anthropic](https://console.anthropic.com) | Yorum analizi | Ücretli (token başına) |
| Alan adı | `taplatr.com` | Yıllık |

## 2. Cloudflare kurulumu

### Alan adını ekle
Cloudflare → Add a site → alan adını gir → DNS kayıtlarını taşı

### KV namespace oluştur
Workers & Pages → KV → Create namespace → ad: `KARTLAR`

### Worker oluştur
1. Workers & Pages → Create → Worker → ad: `taplink`
2. Deploy → Edit code → `worker.js` içeriğini yapıştır → Deploy
3. Settings → Variables:
   - **KV Namespace Bindings:** Variable name `KARTLAR` → oluşturduğun namespace
   - **Environment Variables:** `ADMIN_KEY` → uzun rastgele bir değer, **Encrypt** işaretle

### Route'ları ekle
Worker → Settings → Domains & Routes → Add → **Route** (Custom Domain değil):

```
taplatr.com/r/*
taplatr.com/p/*
taplatr.com/api/*
```

Zone: `taplatr.com`

### Pages projesi (tanıtım sitesi)
1. Workers & Pages → Create → Pages → Upload assets
2. Proje adı: `tapla`
3. `index.html` içeren zip yükle
4. Custom domains → `taplatr.com` ekle

> **Sıralama önemli:** Önce Worker'ın custom domain kaydını sil (varsa),
> sonra Pages'e domain ekle, en son Worker route'larını ekle.

### Doğrulama

```
https://taplatr.com          → tanıtım sitesi
https://taplatr.com/p/       → "Tapla Panel" giriş sayfası
https://taplatr.com/api/isletme → "yetkisiz" (401)
```

## 3. Yerel kurulum

```powershell
cd C:\Projeler\yorumrapor

python -m venv venv
.\venv\Scripts\pip install -r requirements.txt

copy .env.example .env
notepad .env    # değerleri doldur
```

`.env` içeriği:
```
WORKER_URL=https://taplatr.com
ADMIN_KEY=cloudflare_secret_ile_ayni_deger
APIFY_TOKEN=apify_api_...
ANTHROPIC_API_KEY=sk-ant-...
```

## 4. İlk kart

```powershell
.\venv\Scripts\python.exe kart_yonet.py uret 10
.\venv\Scripts\python.exe kart_yonet.py ata KOD "Test" "https://google.com" "Test kart"
```

Tarayıcıda `https://taplatr.com/r/KOD` aç — yönlendirme çalışmalı.

## 5. NFC kart yazma

Telefonda **NFC Tools** uygulaması:

1. Write → Add a record → URL/URI
2. `https://taplatr.com/r/KOD`
3. Write → kartı telefona değdir
4. Read ile doğrula
5. Test et
6. **Test SONRASI:** Other → Lock tag (geri alınamaz)
