"""
Kart yonetimi: kod uret, sunucuya tanimla, listeyi CSV'de tut.

Kullanim:
  # 1) Bos kart uret (henuz isletmeye atanmamis, karta yazilacak link hazir)
  python kart_yonet.py uret 10

  # 2) Bir kodu isletmeye ata (satis aninda)
  python kart_yonet.py ata a7x2k9 "Kafe ABC" "https://search.google.com/local/writereview?placeid=XXX"

  # 3) Karta ad ver (panelde "Masa 1" gibi gorunur)
  python kart_yonet.py adlandir a7x2k9 "Masa 1"

  # 4) Karti isletmeden cikar (kart calismaya devam eder)
  python kart_yonet.py cikar a7x2k9

  # 5) Istatistige bak
  python kart_yonet.py stat a7x2k9

  # 6) Tum kartlari listele
  python kart_yonet.py liste

Not: 'ata' komutuna 4. arguman olarak ad da verebilirsin:
  python kart_yonet.py ata a7x2k9 "Kafe ABC" "YORUM_LINKI" "Masa 1"

.env dosyasina su iki satiri ekle:
  WORKER_URL=https://taplink.SENIN.workers.dev
  ADMIN_KEY=belirledigin-gizli-anahtar
"""
import csv
import os
import random
import string
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
load_dotenv()

CSV_YOL = Path(__file__).parent / "kartlar.csv"
ALFABE = string.ascii_lowercase + string.digits


def _ayar(ad: str) -> str:
    d = os.environ.get(ad)
    if not d:
        print(f"HATA: .env dosyasinda {ad} tanimli degil.")
        sys.exit(1)
    return d.rstrip("/")


def _kodlar() -> set:
    if not CSV_YOL.exists():
        return set()
    with open(CSV_YOL, encoding="utf-8") as f:
        return {r["kod"] for r in csv.DictReader(f)}


def _satir_ekle(satir: dict):
    yeni = not CSV_YOL.exists()
    with open(CSV_YOL, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["kod", "link", "isletme", "hedef", "isim", "not"])
        if yeni:
            w.writeheader()
        w.writerow(satir)


def _guncelle(kod: str, isletme: str, hedef: str, isim: str = ""):
    rows = list(csv.DictReader(open(CSV_YOL, encoding="utf-8")))
    for r in rows:
        r.setdefault("isim", "")
        if r["kod"] == kod:
            r["isletme"], r["hedef"] = isletme, hedef
            if isim:
                r["isim"] = isim
    with open(CSV_YOL, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["kod", "link", "isletme", "hedef", "isim", "not"])
        w.writeheader()
        w.writerows(rows)


def uret(adet: int):
    """Rastgele kod uret, karta yazilacak linki CSV'ye yaz. Sunucuya henuz gitmez."""
    mevcut = _kodlar()
    worker = _ayar("WORKER_URL")
    for _ in range(adet):
        while True:
            kod = "".join(random.choices(ALFABE, k=6))
            if kod not in mevcut:
                break
        mevcut.add(kod)
        link = f"{worker}/r/{kod}"
        _satir_ekle({"kod": kod, "link": link, "isletme": "", "hedef": "", "isim": "", "not": ""})
        print(f"{kod}  ->  {link}")
    print(f"\n{adet} kod uretildi, kartlar.csv dosyasina yazildi.")
    print("Bu linkleri karta yaz. Isletmeye atama satis aninda 'ata' komutuyla yapilir.")


def ata(kod: str, isletme: str, hedef: str, isim: str = ""):
    worker, key = _ayar("WORKER_URL"), _ayar("ADMIN_KEY")
    r = requests.get(f"{worker}/api/ekle", params={
        "key": key, "kod": kod, "hedef": hedef, "isletme": isletme,
    }, timeout=30)
    if r.status_code != 200:
        print(f"HATA {r.status_code}: {r.text}")
        sys.exit(1)
    print(r.text)
    if CSV_YOL.exists():
        _guncelle(kod, isletme, hedef, isim)
    print(f"Karta yazili link artik {isletme} hedefine gidiyor.")
    if isim:
        print(f"Kart adi: {isim}")


def cikar(kod: str):
    """Karti bagli oldugu isletmeden cikar.

    - Sunucuda kartin isletme bagi (token) silinir -> okutmalari artik
      o isletmenin paneline sayilmaz
    - CSV'de isletme/isim alanlari temizlenir
    - Kart kodu ve NFC'ye yazili link DEGISMEZ, kart calismaya devam eder
    """
    worker, key = _ayar("WORKER_URL"), _ayar("ADMIN_KEY")

    if not CSV_YOL.exists():
        print("kartlar.csv yok.")
        sys.exit(1)
    rows = list(csv.DictReader(open(CSV_YOL, encoding="utf-8")))
    for r in rows:
        r.setdefault("isim", "")

    kayit = next((r for r in rows if r["kod"] == kod), None)
    if not kayit:
        print(f"Kod bulunamadi: {kod}")
        sys.exit(1)

    eski_isletme = kayit.get("isletme", "").strip()
    hedef = kayit.get("hedef", "").strip()
    if not eski_isletme:
        print(f"{kod} zaten bir isletmeye bagli degil.")
        return
    if not hedef:
        print(f"UYARI: {kod} icin hedef link kayitli degil, kart yonlendirmesi bozulabilir.")
        if input("Devam edilsin mi? (e/h): ").strip().lower() != "e":
            return

    r2 = requests.get(f"{worker}/api/ekle", params={
        "key": key, "kod": kod, "hedef": hedef, "isletme": "",
    }, timeout=30)
    if r2.status_code != 200 or not r2.text.startswith("OK:"):
        print(f"HATA: sunucu guncellenemedi -> {r2.status_code} {r2.text[:100]}")
        sys.exit(1)

    kayit["isletme"] = ""
    kayit["isim"] = ""
    with open(CSV_YOL, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["kod", "link", "isletme", "hedef", "isim", "not"])
        w.writeheader()
        w.writerows(rows)

    print(f"{kod} -> '{eski_isletme}' isletmesinden cikarildi.")
    print(f"  Kart hala calisiyor, {hedef[:50]}... adresine gidiyor.")
    print(f"\nSON ADIM - paneli tazele ki kart listeden dussun:")
    print(f'  python panel_yonet.py ac "{eski_isletme}"')


def adlandir(kod: str, isim: str):
    """Var olan bir karta ad ver (Masa 1, Kasa, Giris...)."""
    if not CSV_YOL.exists():
        print("kartlar.csv yok.")
        sys.exit(1)
    rows = list(csv.DictReader(open(CSV_YOL, encoding="utf-8")))
    for r in rows:
        r.setdefault("isim", "")
    bulundu = False
    for r in rows:
        if r["kod"] == kod:
            r["isim"] = isim
            bulundu = True
    if not bulundu:
        print(f"Kod bulunamadi: {kod}")
        sys.exit(1)
    with open(CSV_YOL, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["kod", "link", "isletme", "hedef", "isim", "not"])
        w.writeheader()
        w.writerows(rows)
    print(f"{kod} -> \"{isim}\"")
    print("Panele yansimasi icin:  python panel_yonet.py ac \"ISLETME ADI\"")


def stat(kod: str):
    worker, key = _ayar("WORKER_URL"), _ayar("ADMIN_KEY")
    r = requests.get(f"{worker}/api/stat/{kod}", params={"key": key}, timeout=30)
    if r.status_code != 200:
        print(f"HATA {r.status_code}: {r.text}")
        sys.exit(1)
    d = r.json()
    print(f"Kart: {d['kod']}  ({d.get('isletme') or 'atanmamis'})")
    print(f"Toplam okutma: {d['toplam_tap']}")
    gunluk = d.get("gunluk", {})
    if gunluk:
        print("\nGun gun:")
        for gun in sorted(gunluk):
            print(f"  {gun}: {gunluk[gun]}")


def liste():
    if not CSV_YOL.exists():
        print("Henuz kart uretilmemis.")
        return
    for r in csv.DictReader(open(CSV_YOL, encoding="utf-8")):
        durum = r["isletme"] or "(bos)"
        print(f"{r['kod']}  {durum:<28} {r['link']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    komut = sys.argv[1]
    try:
        if komut == "uret":
            uret(int(sys.argv[2]))
        elif komut == "ata":
            isim = sys.argv[5] if len(sys.argv) > 5 else ""
            ata(sys.argv[2], sys.argv[3], sys.argv[4], isim)
        elif komut == "adlandir":
            adlandir(sys.argv[2], sys.argv[3])
        elif komut == "cikar":
            cikar(sys.argv[2])
        elif komut == "stat":
            stat(sys.argv[2])
        elif komut == "liste":
            liste()
        else:
            print(__doc__)
    except IndexError:
        print(__doc__)
