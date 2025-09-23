import requests
import time
import pygame
import json
import os
import sys

API_KEY = "" #api key girin
CATEGORY_ID = "1010000730" #cs2 ilan id (başka oyunların itemlerine bakmak için id değiştirin) 
CHECK_INTERVAL = 75  #sorgulama aralığı


def resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def load_items() -> dict:
    path = resource_path("items.json")
    if not os.path.exists(path):
        print("❌ items.json bulunamadı! Boş liste döndürülüyor.")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ items.json okunamadı: {e}")
        return {}


def get_listings(name: str, min_price=0, max_price=999999) -> dict:
    url = f"https://apilisting.bynogame.com/{CATEGORY_ID}-last"
    params = {
        "apikey": API_KEY,
        "name": name,
        "minPrice": min_price,
        "maxPrice": max_price,
        "limit": 10,
        "page": 1,
        "sandbox": "false"
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"❌ API hatası: {e}")
        return {"data": []}


def check_prices(items_to_track: dict) -> list:
    alerts = []
    for item_name, target_price in items_to_track.items():
        data = get_listings(item_name)
        if "data" not in data:
            continue

        for listing in data["data"]:
            price = listing.get("price", 0)
            url = listing.get("listingURls", {}).get("tr", "")
            name = listing.get("name", "Bilinmeyen")

            if price and price > 0 and price < target_price:
                alerts.append(f"✅ {name} şu an {price} TL → {url}")
    return alerts


def play_sound():
    sound_file = resource_path("tradeFound.mp3")
    if not os.path.exists(sound_file):
        print("⚠️ tradeFound.mp3 bulunamadı, ses çalınamadı.")
        return

    try:
        pygame.mixer.init()
        pygame.mixer.music.load(sound_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        print(f"⚠️ Ses çalma hatası: {e}")

if __name__ == "__main__":
    print("📢 Fiyat takip botu çalışıyor...")
    while True:
        items_to_track = load_items()
        if not items_to_track:
            print("⚠️ items.json boş veya okunamadı.")
        else:
            found_alerts = check_prices(items_to_track)
            if found_alerts:
                print("\n".join(found_alerts))
                print("-" * 40)
                play_sound()
            else:
                print("Ucuza satan keriz yok.")

        time.sleep(CHECK_INTERVAL)
