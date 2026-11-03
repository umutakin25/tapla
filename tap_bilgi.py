"""
Rapora eklenecek kart okutma bilgisini sunucudan ceker.

kartlar.csv'de isletme adiyla eslesen kod(lar)i bulur, her biri icin
worker'daki /stat ucundan okutma sayilarini alir ve toplar.

Sunucu kurulu degilse veya kart atanmamissa sessizce None doner —
rapor yine uretilir, sadece okutma kutusu gorunmez.
"""
import csv
import os
from datetime import date, timedelta
from pathlib import Path

import requests

CSV_YOL = Path(__file__).parent / "kartlar.csv"


def _kodlari_bul(isletme: str) -> list[str]:
    if not CSV_YOL.exists():
        return []
    with open(CSV_YOL, encoding="utf-8") as f:
        return [r["kod"] for r in csv.DictReader(f)
                if r.get("isletme", "").strip().lower() == isletme.strip().lower()]


def tap_bilgisi(isletme: str, gun_araligi: int = 30) -> dict | None:
    """
    Donus:
      {"toplam": 412, "donem": 137, "gun_sayisi": 30, "kart_sayisi": 2}
    veya None (sunucu yok / kart atanmamis / hata)
    """
    worker = os.environ.get("WORKER_URL", "").rstrip("/")
    key = os.environ.get("ADMIN_KEY", "")
    if not worker or not key:
        return None

    kodlar = _kodlari_bul(isletme)
    if not kodlar:
        return None

    sinir = (date.today() - timedelta(days=gun_araligi)).isoformat()
    toplam = donem = 0

    for kod in kodlar:
        try:
            r = requests.get(f"{worker}/api/stat/{kod}", params={"key": key}, timeout=15)
            if r.status_code != 200:
                continue
            d = r.json()
            toplam += int(d.get("toplam_tap", 0))
            for gun, adet in (d.get("gunluk") or {}).items():
                if gun >= sinir:
                    donem += int(adet)
        except Exception:
            continue

    if toplam == 0 and donem == 0:
        return None

    return {"toplam": toplam, "donem": donem,
            "gun_sayisi": gun_araligi, "kart_sayisi": len(kodlar)}
