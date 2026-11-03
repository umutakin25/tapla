# Tapla

NFC tabanlı Google yorum toplama ve yapay zekâ destekli müşteri geri bildirim
analiz sistemi. Küçük işletmeler için.

**Durum:** Üretimde · İlk müşteri aktif · Tek geliştirici (Umut)

---

## Ne yapar

Müşteri, işletmedeki NFC kartına telefonunu değdirir → Google yorum sayfası açılır.
Her okutma sayılır. İşletme sahibi kendi panelinden anlık takip eder.
Ayda bir yorumlar yapay zekâ ile analiz edilip rapor üretilir.

```
Müşteri telefonu ──► NFC kart ──► taplatr.com/r/<kod> ──► Google yorum sayfası
                                          │
                                          └──► okutma sayacı (Cloudflare KV)
                                                        │
İşletme sahibi ──► taplatr.com/p/<token> ──────────────┘
                   (PWA panel: okutma + puan + tema analizi)
```

---

## Mimari

İki bağımsız parça:

### 1. Sunucu tarafı — Cloudflare Worker (`worker.js`)

Tek dosya, ~2000 satır, bağımlılık yok. Şunları yapar:

| Yol | İşlev |
|---|---|
| `/r/<kod>` | Kart yönlendirmesi + okutma sayacı |
| `/p/<token>` | İşletme paneli (PWA, HTML gömülü) |
| `/p/manifest.json`, `/p/sw.js`, `/p/ikon-*.png` | PWA varlıkları |
| `/api/p/<token>` | Panel verisi (JSON) |
| `/api/ekle` | Kart tanımla/güncelle |
| `/api/isletme` | İşletme + kart bağlantısı kur |
| `/api/ozet` | Analiz özetini yaz (POST) |
| `/api/stat/<kod>` | Kart istatistiği |
| `/api/sifirla` | Panel sayaçlarını sıfırla |

`/api/*` uçları `ADMIN_KEY` ister.

**Veri deposu:** Cloudflare KV (`KARTLAR` binding)

| Anahtar | İçerik |
|---|---|
| `kart:<kod>` | `{hedef, isletme, not, token}` |
| `panel:<token>` | `{toplam, gunluk{}, kartlar{}, son, son_kart}` |
| `isletme:<token>` | `{ad, kodlar[], isimler{}}` |
| `ozet:<token>` | `{puan, onceki_puan, toplam_yorum, temalar[], son_yorumlar[]}` |
| `tap:<kod>` | İşletmeye atanmamış kartların sayacı |
| `dedup:<kod>:<ip>:<ua>` | 60 sn tekrar engelleme (TTL) |

**Ölçek kararı:** Okutmalar yazma anında tek bir `panel:<token>` anahtarında
toplanır. Panel yenileme maliyeti kart sayısından bağımsızdır (sabit 3 KV okuma).
Okuma anında toplama yapılsaydı 30 kartlı bir işletmede tek yenileme 900+ KV
okuma ve 30 list işlemi gerektirirdi — ücretsiz plan limitini aşardı.

### 2. İstemci tarafı — Python CLI

Yerelde çalışır, Worker'ı HTTP üzerinden yönetir.

| Dosya | Görev |
|---|---|
| `main.py` | Rapor üretim akışı (çek → analiz et → raporla → panele gönder) |
| `fetch_reviews.py` | Apify ile Google yorumlarını çeker |
| `analyze.py` | Anthropic API ile tema/duygu analizi |
| `report.py` | HTML rapor üretir |
| `state.py` | Dönemsel karşılaştırma için durum takibi |
| `kart_yonet.py` | Kart üret, ata, adlandır, çıkar, istatistik |
| `panel_yonet.py` | Panel aç, veri gönder, sıfırla, listele |
| `tap_bilgi.py` | Worker'dan okutma verisi çeker |

### 3. Tanıtım sitesi

`site/index.html` — tek dosya, Cloudflare Pages'te barındırılır.

---

## Kurulum

### Gereksinimler

- Python 3.10+
- Cloudflare hesabı (Workers + KV + Pages, ücretsiz plan yeterli)
- Apify hesabı (Google Maps Reviews Scraper)
- Anthropic API anahtarı

### Adımlar

```bash
# 1. Bağımlılıklar
python -m venv venv
venv/Scripts/pip install -r requirements.txt   # Windows
# source venv/bin/activate && pip install -r requirements.txt   # Linux/Mac

# 2. Ortam değişkenleri
cp .env.example .env
# .env dosyasını doldur

# 3. Cloudflare
#    - Worker oluştur (adı: taplink), worker.js içeriğini yapıştır
#    - KV namespace oluştur, "KARTLAR" adıyla binding ekle
#    - Secret ekle: ADMIN_KEY
#    - Route ekle: <domain>/r/*, <domain>/p/*, <domain>/api/*
#    - Pages projesi oluştur, site/index.html yükle
```

Detaylı kurulum: [`docs/KURULUM.md`](docs/KURULUM.md)

---

## Kullanım

```bash
# Kart üret
python kart_yonet.py uret 10

# Karta işletme ve hedef ata
python kart_yonet.py ata KOD "İşletme Adı" "GOOGLE_WRITEREVIEW_LINKI" "Masa 1"

# Kart adını değiştir
python kart_yonet.py adlandir KOD "Kasa"

# Kartı işletmeden çıkar (kart çalışmaya devam eder)
python kart_yonet.py cikar KOD

# Panel aç (müşteriye verilecek linki üretir)
python panel_yonet.py ac "İşletme Adı"

# Rapor üret (+ panel otomatik güncellenir)
python main.py "İşletme Adı" "GOOGLE_MAPS_LINKI"

# Test okutmalarını temizle
python panel_yonet.py sifirla "İşletme Adı"
```

---

## Önemli tasarım kararları

**Kart kodu kalıcı, kart adı serbest.** Kod NFC çipine yazılır ve URL'in
parçasıdır, değiştirilemez. Ad (`Masa 1`, `Kasa`) ayrı tutulur, istenildiği
zaman değiştirilir.

**Panel erişimi token ile, şifresiz.** Uzun rastgele token URL'de taşınır.
Bu ölçekte yeterli kabul edildi; şifre eklemek müşteri sürtünmesini artırırdı.

**Yorum verisi anlık değil.** Google yeni yorumları push etmiyor. Kart okutma
anlık, yorum/puan verisi rapor üretildiğinde tazelenir. Bu ürün vaadinde
açıkça belirtilir.

**Service worker network-first.** Cache-first denendi, worker güncellemeleri
istemciye ulaşmadı. Şimdi önce ağ, ağ yoksa önbellek. Sürüm numarası panelin
altında gösterilir (hata ayıklama için).

**Yönetim uçları `/api/` altında.** Tanıtım sitesi kök adreste (Pages) olduğu
için `/isletme` gibi çıplak yollar Pages'e gidip HTML döndürüyordu.

---

## Bilinen sınırlar

- Cloudflare ücretsiz plan: 1.000 KV yazma/gün. Her okutma 2 yazma harcar,
  yani günde ~500 okutma. Üstünde Workers Paid ($5/ay) gerekir.
- Panel grafiği son 60 günü tutar, eskisi otomatik silinir.
- Raporlar aynı dosya adına yazılır, geçmiş arşivlenmez (iyileştirilebilir).
- Tek geliştirici, test altyapısı Node tabanlı manuel senaryolarla sınırlı.

---

## Belgeler

| Dosya | İçerik |
|---|---|
| [`docs/MIMARI.md`](docs/MIMARI.md) | Teknik mimari detayları |
| [`docs/KURULUM.md`](docs/KURULUM.md) | Sıfırdan kurulum |
| [`docs/SORUN_GIDERME.md`](docs/SORUN_GIDERME.md) | Yaşanmış hatalar ve çözümleri |

---

## Güvenlik

Müşteri verisi ve anahtarlar repoya girmez, `.gitignore` ile hariç tutulur:

- `.env` — API anahtarları
- `kartlar.csv` — kart kodları ve müşteri bilgileri
- `panel_adresleri.csv` — müşteri panel token'ları
- `*_rapor.html`, `*_yorumlar.json` — müşteri yorum verisi

Anahtar sızarsa: Apify ve Anthropic'te token'ı iptal edip yenisini üret,
Cloudflare'de `ADMIN_KEY` secret'ını değiştir.

---

## Lisans

Özel proje, açık lisans yok.
