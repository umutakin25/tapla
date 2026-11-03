"""
Kullanim:
    python main.py "Kafe ABC" "https://maps.google.com/..."

Ilk calistirmada tam tarama yapar.
Sonraki aylarda ayni komutu calistir: sadece YENI yorumlari analiz eder,
gecen donemle kiyaslar. Hafiza data/<slug>.json icinde tutulur.
"""
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fetch_reviews import fetch_reviews
from analyze import analyze_reviews
from report import render_report
from state import (durum_yukle, durum_kaydet, yenileri_ayikla,
                   onceki_rapor, durumu_guncelle)
from tap_bilgi import tap_bilgisi


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    isletme, maps_url = sys.argv[1], sys.argv[2]
    slug = "".join(c if c.isalnum() else "_" for c in isletme.lower())

    tum = fetch_reviews(maps_url)
    Path(f"{slug}_yorumlar.json").write_text(
        json.dumps(tum, ensure_ascii=False, indent=2), encoding="utf-8")
    if not tum:
        print("Hic metinli yorum bulunamadi.")
        sys.exit(1)

    durum = durum_yukle(slug)
    yeni, eski = yenileri_ayikla(tum, durum)
    onceki = onceki_rapor(durum)

    if onceki and not yeni:
        print(f"[bilgi] Gecen rapordan beri yeni yorum yok ({len(tum)} yorum sabit).")
        print("[bilgi] Rapor yine de uretiliyor, degisim yok olarak isaretlenecek.")

    print(f"[bilgi] {len(yeni)} yeni / {len(eski)} onceden gorulmus yorum")

    analiz = analyze_reviews(yeni, eski, onceki)
    analiz["_yeni_yorum_sayisi"] = len(yeni)
    analiz["_onceki"] = onceki
    Path(f"{slug}_analiz.json").write_text(
        json.dumps(analiz, ensure_ascii=False, indent=2), encoding="utf-8")

    tap = tap_bilgisi(isletme)
    if tap:
        print(f"[tap] {tap['toplam']} toplam okutma, son 30 gunde {tap['donem']}")

    render_report(isletme, analiz, len(tum), f"{slug}_rapor.html", tap=tap)

    durum_kaydet(slug, durumu_guncelle(durum, tum, analiz, len(yeni)))

    try:
        from panel_yonet import _token_bul
        if _token_bul(isletme):
            import subprocess
            subprocess.run([sys.executable, "panel_yonet.py", "gonder", isletme], check=False)
    except Exception as e:
        print(f"[panel] guncellenemedi ({e}) - elle: python panel_yonet.py gonder \"{isletme}\"")

    print("\nBitti! Raporu tarayicida ac, Ctrl+P ile PDF'e cevir.")


if __name__ == "__main__":
    main()
