"""
Adim 3: Analiz JSON'unu HTML rapora cevir.
Cikti tek dosyalik, kendine yeten bir .html — tarayicida ac,
Ctrl+P -> "PDF olarak kaydet" ile musteriyle paylas.
"""
import base64
import io
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent / "templates"


def _trend_grafigi(aylik_trend: list[dict]) -> str | None:
    """Aylik ortalama puan grafigini cizip base64 PNG dondurur (HTML'e gomulecek)."""
    if not aylik_trend or len(aylik_trend) < 2:
        return None

    aylar = [t["ay"] for t in aylik_trend]
    ortalamalar = [t["ortalama"] for t in aylik_trend]
    sayilar = [t.get("yorum_sayisi", 0) for t in aylik_trend]

    fig, ax1 = plt.subplots(figsize=(8, 2.8), dpi=150)
    ax1.plot(aylar, ortalamalar, marker="o", color="#0FA3A3", linewidth=2.5)
    ax1.set_ylim(1, 5)
    ax1.set_ylabel("Ortalama puan", color="#10243E", fontsize=9)
    ax1.grid(axis="y", color="#E3E9F0")
    ax1.tick_params(labelsize=8)

    ax2 = ax1.twinx()
    ax2.bar(aylar, sayilar, alpha=0.18, color="#10243E")
    ax2.set_ylabel("Yorum sayısı", color="#5A6B7B", fontsize=9)
    ax2.tick_params(labelsize=8)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def render_report(isletme: str, analiz: dict, toplam_yorum: int, cikti: str,
                  tap: dict | None = None) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("rapor.html")

    onceki = analiz.get("_onceki")
    delta_puan, delta_sinif = None, "flat"
    if onceki and onceki.get("ortalama") and analiz.get("ortalama_puan"):
        fark = round(analiz["ortalama_puan"] - onceki["ortalama"], 1)
        if fark > 0:
            delta_puan, delta_sinif = f"+{fark}", "up"
        elif fark < 0:
            delta_puan, delta_sinif = f"{fark}", "down"
        else:
            delta_puan, delta_sinif = "=", "flat"

    html = template.render(
        isletme=isletme,
        a=analiz,
        toplam_yorum=toplam_yorum,
        yeni_yorum=analiz.get("_yeni_yorum_sayisi"),
        onceki=onceki,
        delta_puan=delta_puan,
        delta_sinif=delta_sinif,
        tarih=date.today().strftime("%d.%m.%Y"),
        grafik_b64=_trend_grafigi(analiz.get("aylik_trend", [])),
        tap=tap,
    )

    Path(cikti).write_text(html, encoding="utf-8")
    print(f"[rapor] Yazildi: {cikti}")
    return cikti
