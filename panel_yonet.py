"""
Panel yonetimi: isletme hesabi ac, panel verisini gonder.

Kullanim:
  # 1) Isletmeye panel hesabi ac (kartlar.csv'den kodlari otomatik bulur)
  python panel_yonet.py ac "Kafe ABC"

  # 2) Son analiz raporunu panele gonder
  python panel_yonet.py gonder "Kafe ABC"

  # 3) Test okutmalarini sifirla (musteriye teslimden once)
  python panel_yonet.py sifirla "Kafe ABC"

  # 4) Panel adreslerini listele
  python panel_yonet.py liste

Panelleri musteriye "panel_adresleri.csv" dosyasindaki linkle veriyorsun.
"""
import csv
import json
import os
import random
import string
import sys
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv
load_dotenv()

KLASOR = Path(__file__).parent
KART_CSV = KLASOR / "kartlar.csv"
PANEL_CSV = KLASOR / "panel_adresleri.csv"
ALFABE = string.ascii_letters + string.digits


def _ayar(ad):
    d = os.environ.get(ad)
    if not d:
        print(f"HATA: .env dosyasinda {ad} yok.")
        sys.exit(1)
    return d.rstrip("/")


def _slug(ad):
    return "".join(c if c.isalnum() else "_" for c in ad.lower())


def _kodlari_bul(isletme):
    if not KART_CSV.exists():
        return []
    with open(KART_CSV, encoding="utf-8") as f:
        return [r["kod"] for r in csv.DictReader(f)
                if r.get("isletme", "").strip().lower() == isletme.strip().lower()]


def _isimleri_bul(isletme):
    """{kod: isim} - sadece adi olan kartlar."""
    if not KART_CSV.exists():
        return {}
    out = {}
    with open(KART_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("isletme", "").strip().lower() == isletme.strip().lower()
                    and r.get("isim", "").strip()):
                out[r["kod"]] = r["isim"].strip()
    return out


def _paneller():
    if not PANEL_CSV.exists():
        return []
    with open(PANEL_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _panel_yaz(satirlar):
    with open(PANEL_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["isletme", "token", "panel_linki"])
        w.writeheader()
        w.writerows(satirlar)


def _token_bul(isletme):
    for r in _paneller():
        if r["isletme"].strip().lower() == isletme.strip().lower():
            return r["token"]
    return None


def ac(isletme):
    worker, key = _ayar("WORKER_URL"), _ayar("ADMIN_KEY")
    kodlar = _kodlari_bul(isletme)
    if not kodlar:
        print(f"UYARI: '{isletme}' adina atanmis kart bulunamadi.")
        print("Once kart ata:  python kart_yonet.py ata KOD \"" + isletme + "\" \"YORUM_LINKI\"")
        if input("Yine de panel acilsin mi? (e/h): ").strip().lower() != "e":
            return

    token = _token_bul(isletme)
    yeni = token is None
    if yeni:
        mevcut = {r["token"] for r in _paneller()}
        while True:
            token = "".join(random.choices(ALFABE, k=12))
            if token not in mevcut:
                break

    isimler = _isimleri_bul(isletme)
    isim_param = "|".join(f"{k}={v}" for k, v in isimler.items())
    r = requests.get(f"{worker}/api/isletme", params={
        "key": key, "token": token, "ad": isletme,
        "kodlar": ",".join(kodlar), "isimler": isim_param}, timeout=30)
    if r.status_code != 200:
        print(f"HATA {r.status_code}: {r.text}")
        sys.exit(1)
    if not r.text.startswith("OK:"):
        print("HATA: Sunucu beklenen cevabi vermedi.")
        print(f"  Gelen cevap: {r.text[:120]}")
        print("\n  Sebep: Cloudflare'deki worker eski surum, /isletme yolunu tanimiyor.")
        print("  Cozum: worker.js dosyasinin icerigini Cloudflare'e yapistirip Deploy et,")
        print("         sonra /p/* ve /api/* route'larini ekle. Detay: KURULUM_PANEL.md")
        sys.exit(1)
    print(r.text)

    link = f"{worker}/p/{token}"
    satirlar = [x for x in _paneller() if x["token"] != token]
    satirlar.append({"isletme": isletme, "token": token, "panel_linki": link})
    _panel_yaz(satirlar)

    try:
        d = requests.get(f"{worker}/api/p/{token}", timeout=20)
        if d.status_code != 200:
            print(f"UYARI: panel dogrulanamadi (HTTP {d.status_code}).")
            print("  /api/* route'u eklenmemis olabilir — KURULUM_PANEL.md ADIM 2.")
        else:
            print("Dogrulama: panel erisilebilir durumda.")
    except Exception as e:
        print(f"UYARI: dogrulama yapilamadi ({e})")

    adli = len(_isimleri_bul(isletme))
    print(f"\n{'Panel acildi' if yeni else 'Panel guncellendi'}: {len(kodlar)} kart bagli"
          + (f", {adli} tanesi adlandirilmis" if adli else ""))
    if not adli and len(kodlar) > 1:
        print("  Ipucu: kartlara ad ver ki panelde 'Masa 1' gibi gorunsun:")
        print(f"    python kart_yonet.py adlandir {kodlar[0]} \"Masa 1\"")
    print(f"Musteriye verilecek link:\n  {link}")
    print("\nMusteriye soyle: linki telefonda ac, tarayici menusunden")
    print("'Ana ekrana ekle' de — uygulama gibi calisir.")


def gonder(isletme):
    worker, key = _ayar("WORKER_URL"), _ayar("ADMIN_KEY")
    token = _token_bul(isletme)
    if not token:
        print(f"'{isletme}' icin panel yok. Once:  python panel_yonet.py ac \"{isletme}\"")
        sys.exit(1)

    slug = _slug(isletme)
    analiz_yol = KLASOR / f"{slug}_analiz.json"
    yorum_yol = KLASOR / f"{slug}_yorumlar.json"
    if not analiz_yol.exists():
        print(f"Analiz dosyasi yok: {analiz_yol.name}")
        print(f"Once rapor uret:  python main.py \"{isletme}\" \"MAPS_LINKI\"")
        sys.exit(1)

    analiz = json.loads(analiz_yol.read_text(encoding="utf-8"))
    onceki = analiz.get("_onceki") or {}

    son_yorumlar = []
    if yorum_yol.exists():
        tum = json.loads(yorum_yol.read_text(encoding="utf-8"))
        tum.sort(key=lambda y: y.get("date", ""), reverse=True)
        son_yorumlar = [{"text": (y.get("text") or "")[:2500],
                         "stars": y.get("stars"),
                         "date": y.get("date", "")} for y in tum[:8]]

    ozet = {
        "puan": analiz.get("ortalama_puan"),
        "onceki_puan": onceki.get("ortalama"),
        "toplam_yorum": len(json.loads(yorum_yol.read_text(encoding="utf-8"))) if yorum_yol.exists() else None,
        "yeni_yorum": analiz.get("_yeni_yorum_sayisi"),
        "guncelleme": date.today().strftime("%d.%m.%Y"),
        "temalar": [{"tema": t.get("tema"), "duygu": t.get("duygu"),
                     "yorum_sayisi": t.get("yorum_sayisi"), "yon": t.get("yon")}
                    for t in analiz.get("temalar", [])],
        "son_yorumlar": son_yorumlar,
    }

    r = requests.post(f"{worker}/api/ozet", params={"key": key, "token": token},
                      data=json.dumps(ozet, ensure_ascii=False).encode("utf-8"), timeout=30)
    if r.status_code != 200:
        print(f"HATA {r.status_code}: {r.text}")
        sys.exit(1)
    if not r.text.startswith("OK:"):
        print("HATA: Sunucu beklenen cevabi vermedi.")
        print(f"  Gelen cevap: {r.text[:120]}")
        print("  Worker eski surum olabilir — KURULUM_PANEL.md ADIM 1'i uygula.")
        sys.exit(1)
    print(r.text)
    print(f"\nPanel guncellendi: {worker}/p/{token}")
    print(f"  Puan {ozet['puan']} · {len(ozet['temalar'])} tema · {len(son_yorumlar)} yorum")
    if son_yorumlar:
        enuzun = max(len(y["text"]) for y in son_yorumlar)
        print(f"  En uzun yorum: {enuzun} karakter (sinir 2500)")


def sifirla(isletme):
    """Isletmenin panel sayaclarini sifirla (test okutmalarini temizlemek icin).

    Silinen: toplam okutma, gunluk grafik, kart bazli sayaclar, son okutma.
    Korunan: panel linki, kart baglantilari, kart isimleri, Google analiz ozeti.
    """
    worker, key = _ayar("WORKER_URL"), _ayar("ADMIN_KEY")
    token = _token_bul(isletme)
    if not token:
        print(f"'{isletme}' icin panel yok.")
        sys.exit(1)

    try:
        v = requests.get(f"{worker}/api/p/{token}", timeout=20).json()
        print(f"{v.get('ad')} - su anki durum:")
        print(f"  toplam okutma : {v.get('tap', {}).get('toplam', 0)}")
        print(f"  kart sayaclari: {v.get('tap', {}).get('kartlar', {})}")
    except Exception:
        pass

    print("\nSilinecek: toplam okutma, gunluk grafik, kart sayaclari, son okutma")
    print("Korunacak: panel linki, kartlar, kart isimleri, Google analiz ozeti")
    if input("\nSifirlansin mi? (evet yaz): ").strip().lower() != "evet":
        print("Iptal edildi.")
        return

    r = requests.get(f"{worker}/api/sifirla", params={"key": key, "token": token}, timeout=30)
    if r.status_code != 200 or not r.text.startswith("OK:"):
        print(f"HATA {r.status_code}: {r.text[:150]}")
        sys.exit(1)
    print(r.text)
    print("\nPaneli acip Ctrl+Shift+R yap (telefonda uygulamayi kapat-ac).")


def liste():
    satirlar = _paneller()
    if not satirlar:
        print("Henuz panel acilmamis.")
        return
    for r in satirlar:
        kodlar = _kodlari_bul(r["isletme"])
        print(f"{r['isletme']:<40} {len(kodlar)} kart  {r['panel_linki']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    k = sys.argv[1]
    try:
        if k == "ac":
            ac(sys.argv[2])
        elif k == "gonder":
            gonder(sys.argv[2])
        elif k == "sifirla":
            sifirla(sys.argv[2])
        elif k == "liste":
            liste()
        else:
            print(__doc__)
    except IndexError:
        print(__doc__)
