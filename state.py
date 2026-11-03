"""
Adim 0: Hafiza. Hangi isletmenin hangi yorumlarini daha once gorduk?

Her isletme icin data/<slug>.json dosyasi tutulur:
{
  "gorulen": ["hash1", "hash2", ...],        # daha once analiz edilen yorumlar
  "gecmis": [                                 # her ayki rapor ozeti
     {"tarih": "2026-06-21", "ortalama": 4.6, "yeni_yorum": 39,
      "toplam_yorum": 39, "temalar": {"fiyatlar": -0.4, ...}}
  ]
}
"""
import hashlib
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def _yol(slug: str) -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    return DATA_DIR / f"{slug}.json"


def yorum_kimligi(yorum: dict) -> str:
    """Yorumun parmak izi. Ayni yorum tekrar gelirse ayni hash cikar."""
    ham = f"{yorum.get('date','')}|{yorum.get('stars','')}|{yorum.get('text','')[:120]}"
    return hashlib.md5(ham.encode("utf-8")).hexdigest()[:16]


def durum_yukle(slug: str) -> dict:
    p = _yol(slug)
    if not p.exists():
        return {"gorulen": [], "gecmis": []}
    return json.loads(p.read_text(encoding="utf-8"))


def durum_kaydet(slug: str, durum: dict) -> None:
    _yol(slug).write_text(
        json.dumps(durum, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def yenileri_ayikla(tum_yorumlar: list[dict], durum: dict) -> tuple[list, list]:
    """
    Donus: (yeni_yorumlar, onceki_yorumlar)
    Ilk calistirmada hepsi 'yeni' sayilir — ilk rapor zaten tam tarama olmali.
    """
    gorulen = set(durum.get("gorulen", []))
    yeni, eski = [], []
    for y in tum_yorumlar:
        (eski if yorum_kimligi(y) in gorulen else yeni).append(y)
    return yeni, eski


def onceki_rapor(durum: dict) -> dict | None:
    gecmis = durum.get("gecmis", [])
    return gecmis[-1] if gecmis else None


def durumu_guncelle(durum: dict, tum_yorumlar: list[dict], analiz: dict,
                    yeni_sayisi: int) -> dict:
    """Bu ayki raporu gecmise ekle, gorulen yorumlari isaretle."""
    durum["gorulen"] = list({yorum_kimligi(y) for y in tum_yorumlar}
                            | set(durum.get("gorulen", [])))
    from datetime import date
    durum.setdefault("gecmis", []).append({
        "tarih": date.today().isoformat(),
        "ortalama": analiz.get("ortalama_puan"),
        "yeni_yorum": yeni_sayisi,
        "toplam_yorum": len(tum_yorumlar),
        "temalar": {t["tema"]: t["duygu"] for t in analiz.get("temalar", [])},
    })
    return durum
