# Teknik Mimari

## Neden Cloudflare Workers

- Edge'de çalışıyor, soğuk başlatma yok — NFC okutmada gecikme kullanıcıyı kaçırır
- Ücretsiz plan bu ölçek için fazlasıyla yeterli
- KV ile birlikte geliyor, ayrı veritabanı gerekmiyor
- Tek dosya deploy — sunucu yönetimi yok

## Neden tek dosya worker

`worker.js` ~2000 satır ve HTML/CSS/JS panel arayüzünü template literal
olarak içeriyor. Bölmek daha temiz olurdu ama:

- Deploy tek kopyala-yapıştır (Cloudflare panel editöründen)
- Build adımı yok, bundler yok
- Tek geliştirici, karmaşıklık maliyeti getiri sağlamıyor

Proje büyürse Wrangler CLI + modül yapısına geçilmeli.

## Veri akışı

### Okutma anı

```
GET /r/pds34i
  ├─ KV get: kart:pds34i                    (1 okuma)
  ├─ 302 redirect döner (kullanıcı beklemez)
  └─ ctx.waitUntil():
       ├─ KV get: dedup:...                 (1 okuma)
       ├─ KV put: dedup:... (TTL 60)        (1 yazma)
       ├─ KV get: panel:<token>             (1 okuma)
       └─ KV put: panel:<token>             (1 yazma)

Toplam: 3 okuma, 2 yazma
```

`ctx.waitUntil` sayesinde sayaç güncellemesi yönlendirmeyi geciktirmiyor.

### Panel açılışı

```
GET /api/p/<token>
  ├─ KV get: isletme:<token>                (1 okuma)
  ├─ KV get: panel:<token>                  (1 okuma)
  └─ KV get: ozet:<token>                   (1 okuma)

Toplam: 3 okuma — kart sayısından BAĞIMSIZ
```

## Ölçek analizi

3 işletme × 30 kart, günde 200 okutma, işletme başına günde 20 panel bakışı:

| İşlem | Hesap | Toplam | Limit | Doluluk |
|---|---|---|---|---|
| Okuma | 200×3 + 60×3 | 780 | 100.000 | %0.8 |
| Yazma | 200×2 | 400 | 1.000 | %40 |
| List | 0 | 0 | 1.000 | %0 |

**Darboğaz: yazma.** Günde ~500 okutmada limit dolar.
Aşıldığında Workers Paid ($5/ay) 1 milyon yazma veriyor.

### Reddedilen alternatif: okuma anında toplama

Her kartın sayacı ayrı tutulup panel açılışında toplansaydı:

| Kart sayısı | Panel açılışı başına |
|---|---|
| 3 | ~12 okuma + 3 list |
| 30 | ~930 okuma + 30 list |

30 kartta 33 panel açılışı list limitini doldururdu. Kabul edilemez.

## Dedup mantığı

`dedup:<kod>:<ip>:<ua_ilk40>` anahtarı 60 saniye TTL ile yazılıyor.

Amaç: müşteri kartı okutup Google'a gidiyor, geri dönüp tekrar okutuyor —
bu tek ziyaret sayılmalı.

Ayrıca `Sec-Purpose: prefetch` başlığı olan istekler sayılmıyor
(tarayıcı ön yüklemesi gerçek okutma değil).

**Bilinen sınır:** Aynı wifi'deki iki farklı müşteri aynı IP'den gelir.
User-Agent farklıysa ayrı sayılır, aynıysa (aynı model telefon) tek sayılır.
Bu ölçekte kabul edilebilir bir hata payı.

## Service worker stratejisi

**Network-first:** Önce ağdan çek, başarısız olursa önbellekten ver.

```javascript
try {
  const yanit = await fetch(e.request, { cache: 'no-store' });
  if (yanit.status === 200) caches.open(AD).then(c => c.put(e.request, yanit.clone()));
  return yanit;
} catch {
  return await caches.match(e.request);
}
```

Cache-first denendi ve **başarısız oldu**: worker güncellendiğinde istemci
eski HTML'i sunmaya devam etti, kullanıcı günlerce eski paneli gördü.

Sürüm numarası (`tapla-v8`) hem önbellek adında hem panel altında görünüyor.
Yeni sürüm aktifleşince eski önbellekler siliniyor ve sayfa bir kez yenileniyor.

## Güvenlik modeli

| Varlık | Koruma |
|---|---|
| Yönetim uçları | `ADMIN_KEY` query parametresi |
| İşletme paneli | 12 karakterlik rastgele token (URL'de) |
| Kart yönlendirme | Koruma yok (public olmalı) |

Panel şifresiz. Token 62^12 ≈ 3×10^21 olasılık, kaba kuvvet pratik değil.
Şifre eklemek müşteri sürtünmesini artırırdı — bu ölçekte kabul edilen ödünç.

Daha sıkı gerekirse: token'a kısa PIN eklenebilir ya da magic link kurulabilir.

## Test yaklaşımı

Worker, sahte KV ile Node üzerinde çalıştırılıyor:

```javascript
const depo = new Map();
const KV = {
  async get(k) { return depo.has(k) ? depo.get(k) : null; },
  async put(k, v) { depo.set(k, v); },
  async delete(k) { depo.delete(k); },
  async list({prefix}) { /* ... */ },
};
let bekleyen = [];
const ctx = { waitUntil: p => { bekleyen.push(p); return p; } };
const bekle = async () => { await Promise.all(bekleyen); bekleyen = []; };
```

`ctx.waitUntil` mock'unda **beklemeyi unutma** — sayaç asenkron güncelleniyor,
`await bekle()` çağrılmadan kontrol edilirse test yanlış sonuç verir.

Senaryolar: yönlendirme, sayaç doğruluğu, dedup, prefetch, yetkilendirme,
PWA varlıkları, ölçek (30 kart), kart adlandırma, kart çıkarma, sıfırlama.
