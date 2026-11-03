"""
Adim 2: Yorumlari Claude API'ye gonder, yapilandirilmis JSON analiz al.

v2: Rapor artik "bu ay ne degisti" odakli.
 - ilk rapor  -> tum yorumlar taranir (tam fotograf)
 - sonraki ay -> sadece YENI yorumlar analiz edilir, eskiler kiyas icin ozet gecer
"""
import json
import anthropic

MODEL = "claude-sonnet-4-6"

SEMA = """{{
  "genel_ozet": "bu donemin durumunu anlatan 2-3 cumle, Turkce",
  "ortalama_puan": 4.2,
  "donem_ortalamasi": 4.4,
  "aylik_trend": [{{"ay": "2026-05", "ortalama": 4.1, "yorum_sayisi": 12}}],
  "temalar": [
    {{"tema": "servis hizi", "duygu": -0.4, "yorum_sayisi": 8,
      "ornek_alinti": "en fazla 12 kelimelik kisa alinti", "yon": "kotulesti"}}
  ],
  "en_cok_ovgu": ["madde", "madde"],
  "en_cok_sikayet": ["madde", "madde"],
  "degisim_notlari": ["gecen doneme gore dikkat ceken degisim", "..."],
  "aksiyon_onerileri": ["somut oneri", "...", "..."]
}}"""

KURALLAR = """Kurallar:
- duygu: -1 (cok olumsuz) ile +1 (cok olumlu) arasi ondalik sayi.
- yon: "iyilesti" | "kotulesti" | "ayni" | "yeni" degerlerinden biri.
  Onceki donem ozeti verilmediyse hepsi "yeni" olsun.
- temalar: en cok konusulan 4-6 tema, yorum_sayisi'na gore coktan aza sirali.
- aylik_trend: yorum tarihlerinden ay bazinda grupla, eski aydan yeniye sirali.
- ortalama_puan: TUM yorumlarin genel ortalamasi.
- donem_ortalamasi: SADECE bu donemde gelen yeni yorumlarin ortalamasi.
- degisim_notlari: 2-4 madde. Onceki donem yoksa bos liste dondur.
- aksiyon_onerileri: tam 3 madde. Her madde somut olsun: bir sayi, bir zaman
  araligi veya net bir uygulama icersin. "Musteri memnuniyetine onem verin"
  gibi genel gecer cumleler YASAK.
- Tum metinler Turkce."""

ILK_RAPOR = """Asagida bir isletmenin Google Maps yorumlari JSON olarak verilmistir.
Bu ilk rapordur: tum yorumlari analiz et.
SADECE asagidaki semaya uyan gecerli bir JSON dondur. JSON disinda tek karakter yazma.

Sema:
{sema}

{kurallar}

Yorumlar:
{yorumlar_json}
"""

AYLIK_RAPOR = """Asagida bir isletmenin Google Maps yorumlari var.
Bu AYLIK TAKIP raporudur. Odak: bu donemde gelen YENI yorumlar ve gecen doneme gore degisim.

Onceki donem ozeti (kiyas icin, tekrar anlatma):
{onceki_ozet}

Bu donemde gelen YENI yorumlar ({yeni_sayisi} adet) — analizin merkezi bunlar:
{yeni_yorumlar}

Trend hesabi icin gecmis yorumlarin tarih/puan ozeti (metinlerini tekrar yorumlama):
{eski_ozet}

SADECE asagidaki semaya uyan gecerli bir JSON dondur. JSON disinda tek karakter yazma.

Sema:
{sema}

{kurallar}
- genel_ozet ve degisim_notlari YENI yorumlara odaklansin; gecen ay soylenmis
  seyleri tekrar etme, farka isaret et.
"""


def _eski_ozet(eski: list[dict]) -> str:
    """Eski yorumlarin metnini gondermiyoruz; sadece tarih+puan (token tasarrufu)."""
    return json.dumps(
        [{"date": y.get("date"), "stars": y.get("stars")} for y in eski],
        ensure_ascii=False,
    )


def analyze_reviews(yeni: list[dict], eski: list[dict] | None = None,
                    onceki: dict | None = None) -> dict:
    client = anthropic.Anthropic()
    eski = eski or []

    if onceki is None or not eski:
        prompt = ILK_RAPOR.format(
            sema=SEMA, kurallar=KURALLAR,
            yorumlar_json=json.dumps(yeni + eski, ensure_ascii=False),
        )
        print(f"[claude] Ilk rapor: {len(yeni) + len(eski)} yorum analiz ediliyor...")
    else:
        prompt = AYLIK_RAPOR.format(
            sema=SEMA, kurallar=KURALLAR,
            onceki_ozet=json.dumps(onceki, ensure_ascii=False),
            yeni_sayisi=len(yeni),
            yeni_yorumlar=json.dumps(yeni, ensure_ascii=False),
            eski_ozet=_eski_ozet(eski),
        )
        print(f"[claude] Aylik takip: {len(yeni)} yeni yorum analiz ediliyor...")

    msg = client.messages.create(
        model=MODEL, max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = msg.content[0].text.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    analiz = json.loads(raw)
    print("[claude] Analiz tamam")
    return analiz
