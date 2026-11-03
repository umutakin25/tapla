"""
Adim 1: Apify ile Google Maps yorumlarini cek.

C++ karsiligi dusun: bu dosya bir "modul" (header+cpp tek dosyada).
fetch_reviews() disariya acilan tek fonksiyon.
"""
import os
import requests

ACTOR_ID = "compass~google-maps-reviews-scraper"
APIFY_URL = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"


def fetch_reviews(place_url: str, max_reviews: int = 200) -> list[dict]:
    """
    place_url: Isletmenin Google Maps linki (maps.google.com/... seklinde).
               Haritada isletmeyi ac -> Paylas -> linki kopyala.
    Donus: [{"text": "...", "stars": 5, "publishedAtDate": "2026-05-12..."}, ...]
    """
    token = os.environ["APIFY_TOKEN"]

    payload = {
        "startUrls": [{"url": place_url}],
        "maxReviews": max_reviews,
        "reviewsSort": "newest",
        "language": "tr",
    }

    print(f"[apify] Yorumlar cekiliyor (max {max_reviews})... 1-2 dk surebilir")
    resp = requests.post(APIFY_URL, params={"token": token}, json=payload, timeout=600)
    resp.raise_for_status()

    items = resp.json()

    reviews = []
    for it in items:
        text = (it.get("text") or "").strip()
        if not text:
            continue
        reviews.append({
            "text": text,
            "stars": it.get("stars"),
            "date": (it.get("publishedAtDate") or "")[:10],
        })

    print(f"[apify] {len(reviews)} metinli yorum alindi")
    return reviews
