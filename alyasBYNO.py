import os
import sys
import json
import time
import math
import requests
from datetime import datetime
from dotenv import load_dotenv

#Over %70 of this project is made by AI due to some troubles that I couldn't solve about ByNo's API system.
#So it may have some bugs or unresolved problems.

try:
    import msvcrt
except:
    msvcrt = None


def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()
ENV_PATH = os.path.join(BASE_DIR, ".env")

if not os.path.exists(ENV_PATH):
    print("\n.can't find .env")
    api_input = input("Please ENTER ByNoGame API key: ").strip()
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write(f"BYNO_API_KEY={api_input}\n")
        f.write("BYNO_CATEGORY_PATH=1010000730-all\n")
    print(".env created.\n")

load_dotenv(ENV_PATH)

API_KEY = os.environ.get("BYNO_API_KEY", "").strip()
CATEGORY_PATH = os.environ.get("BYNO_CATEGORY_PATH", "1010000730-all").strip()
API_URL = f"https://apilisting.bynogame.com/{CATEGORY_PATH}"

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
EVENT_HISTORY = []

ACTIVE_CHECK_MAX = 20
ACTIVE_CHECK_TIMEOUT = 8

BANNER_RAW = r"""
          (     (              
          )\    )\(       )    
       ((((_)( ((_)\ ) ( /( (  
        )\ _ )\ _(()/( )(_)))\ 
        (_)_\(_) |)(_)|(_)_((_)
         / _ \ | | || / _` (_-<
        /_/ \_\|_|\_, \__,_/__/
                  |__/         

      ★ BYNOGAME API PRICE CHECKER ★
        M = MENU    |    Q = QUIT
============================================================
"""


def enable_ansi_on_windows():
    if os.name != "nt":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
            return
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def rgb(r, g, b):
    return f"\x1b[38;2;{r};{g};{b}m"


def reset():
    return "\x1b[0m"


def hsv_to_rgb(h, s, v):
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    i = i % 6
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    return int(r * 255), int(g * 255), int(b * 255)


def gradient_text_wave(text: str, phase: float):
    lines = text.splitlines(True)
    widths = [len(l.rstrip("\n")) for l in lines if l.strip("\n") != ""]
    max_w = max(widths) if widths else 1

    out = []
    for y, line in enumerate(lines):
        if line == "\n":
            out.append("\n")
            continue

        raw = line.rstrip("\n")
        newline = "\n" if line.endswith("\n") else ""

        for x, ch in enumerate(raw):
            if ch == " ":
                out.append(" ")
                continue
            base = x / max_w
            wave = 0.07 * math.sin((x * 0.35) + (y * 0.9) + phase)
            hue = (base + wave + phase * 0.03) % 1.0

            r, g, b = hsv_to_rgb(hue, 1.0, 1.0)
            out.append(rgb(r, g, b) + ch)

        out.append(reset() + newline)

    return "".join(out)


def banner():
    phase = time.time()
    return gradient_text_wave(BANNER_RAW, phase)


enable_ansi_on_windows()


def now():
    return datetime.now().strftime("%H:%M:%S")


def log_event(msg):
    EVENT_HISTORY.append(f"[{now()}] {msg}")


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def extract_listings(payload):
    if isinstance(payload, dict):
        for k in ("data", "list", "items", "results"):
            if isinstance(payload.get(k), list):
                return payload[k]
        for v in payload.values():
            if isinstance(v, list):
                return v
    if isinstance(payload, list):
        return payload
    return []


def normalize_price(p):
    if isinstance(p, bool) or p is None:
        return None
    if isinstance(p, float):
        return float(p)
    if isinstance(p, int):
        if p >= 10000:
            return p / 100.0
        return float(p)
    if isinstance(p, str):
        s = p.strip()
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", ".")
        try:
            return float(s)
        except:
            return None
    return None


def pick_name(listing: dict):
    for k in ("market_hash_name", "name", "item_name", "productName", "title"):
        v = listing.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def pick_id(listing: dict):
    for k in ("listingID", "listingId", "listing_id", "id", "itemId"):
        v = listing.get(k)
        if isinstance(v, (int, str)) and str(v).strip():
            return str(v).strip()
    return None


def pick_price(listing: dict):
    for k in ("price", "amount", "tl", "price_tl", "salePrice", "unitPrice"):
        if k in listing:
            val = normalize_price(listing.get(k))
            if val is not None:
                return val
    return None


def pick_listing_urls(listing: dict):
    v = listing.get("listingURls")
    if isinstance(v, dict):
        return v
    v = listing.get("listingUrls")
    if isinstance(v, dict):
        return v
    v = listing.get("listing_urls")
    if isinstance(v, dict):
        return v
    return None


def build_bynogame_link(listing: dict, prefer_tr=True):
    urls = pick_listing_urls(listing)
    if isinstance(urls, dict):
        if prefer_tr and isinstance(urls.get("tr"), str) and urls["tr"].startswith("http"):
            return urls["tr"]
        if isinstance(urls.get("en"), str) and urls["en"].startswith("http"):
            return urls["en"]

    for k in ("url", "detailUrl", "detail_url", "seoUrl", "seo_url", "link"):
        v = listing.get(k)
        if isinstance(v, str) and v.startswith("http"):
            return v

    return None


def is_listing_active(url: str):
    if not url or not isinstance(url, str) or not url.startswith("http"):
        return False
    try:
        r = requests.get(
            url,
            timeout=ACTIVE_CHECK_TIMEOUT,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"}
        )
    except requests.RequestException:
        return False

    if r.status_code != 200:
        return False

    html = (r.text or "").lower()

    closed_markers = [
        "ilan kapandı",
        "ilan sona erdi",
        "ilan kaldırıldı",
        "ilan aktif değil",
        "seçtiğiniz ilan artık mevcut değil",
        "listing closed",
        "listing has ended",
        "listing is not available",
        "this listing is no longer available",
        "offer ended",
    ]
    for m in closed_markers:
        if m in html:
            return False

    buy_markers = [
        "sepete ekle",
        "satın al",
        "hemen al",
        "add to cart",
        "buy now",
        "purchase",
        "checkout",
    ]
    for m in buy_markers:
        if m in html:
            return True

    return True


def fetch_lowest_buy_now(item_name: str):
    params = {"apikey": API_KEY}

    try:
        r = requests.get(API_URL, params=params, timeout=25)
    except requests.RequestException:
        return None, None, None, None, "NET_ERR"

    if r.status_code != 200:
        return None, None, None, None, f"HTTP_{r.status_code}"

    try:
        payload = r.json()
    except Exception:
        return None, None, None, None, "BAD_JSON"

    listings = extract_listings(payload)
    if not listings:
        return None, None, None, None, "EMPTY"

    target_lower = item_name.strip().lower()
    candidates = []

    for l in listings:
        if not isinstance(l, dict):
            continue
        nm = pick_name(l).lower()
        if not nm:
            continue
        if not ((nm == target_lower) or (target_lower and target_lower in nm)):
            continue
        pr = pick_price(l)
        if pr is None:
            continue
        candidates.append((pr, l))

    if not candidates:
        return None, None, None, None, "NOT_FOUND"

    candidates.sort(key=lambda x: x[0])

    checked = 0
    for pr, listing in candidates:
        link = build_bynogame_link(listing, prefer_tr=True)
        lid = pick_id(listing)
        checked += 1
        if link and is_listing_active(link):
            return pr, lid, link, listing, None
        if checked >= ACTIVE_CHECK_MAX:
            break

    best_price, best_listing = candidates[0]
    lid = pick_id(best_listing)
    link = build_bynogame_link(best_listing, prefer_tr=True)
    return best_price, lid, link, best_listing, "NO_ACTIVE"


def read_config():
    if not os.path.exists(CONFIG_FILE):
        return None
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def write_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def setup():
    clear()
    print(banner())
    print("First setup starting\n")

    interval = input("Delay Time [30]: ").strip()
    interval = int(interval) if interval.isdigit() else 30

    items = []
    while True:
        n = input("Item name (ENTER Closes): ").strip()
        if not n:
            break
        t = float(input("Target TL: "))
        items.append({"market_hash_name": n, "target_tl": t})

    if not items:
        items = [{"market_hash_name": "StatTrak™ AWP | Duality (Field-Tested)", "target_tl": 228}]

    cfg = {"intervalSeconds": interval, "items": items}
    write_config(cfg)
    return cfg


def menu(cfg):
    while True:
        clear()
        print(banner())
        print("=== ALYAS ===")
        print("1) Current Items")
        print("2) Add Items")
        print("3) Delete Items")
        print("4) Change Delay")
        print("5) Save and Continue")
        print("Q) Quit")

        c = input("> ").lower()

        if c == "1":
            for i, it in enumerate(cfg["items"], 1):
                print(i, it)
            input("Press ENTER to close... ^^")

        elif c == "2":
            n = input("Name: ").strip()
            t = float(input("Target TL: "))
            cfg["items"].append({"market_hash_name": n, "target_tl": t})

        elif c == "3":
            i = int(input("No: ")) - 1
            cfg["items"].pop(i)

        elif c == "4":
            cfg["intervalSeconds"] = int(input("New Delay (in seconds): "))

        elif c == "5":
            write_config(cfg)
            return

        elif c == "q":
            exit()


def keypress():
    if not msvcrt:
        return None
    if msvcrt.kbhit():
        return msvcrt.getwch().lower()
    return None


def print_ui(rows, interval):
    clear()
    print(banner())
    print(f"Delay: {interval}s\n")

    print("{:<45}{:<10}{:<10}{:<10}".format("ITEM", "LOWEST", "TARGET", "STATUS"))
    print("-" * 80)

    for r in rows:
        print("{:<45}{:<10}{:<10}{:<10}".format(*r))

    if EVENT_HISTORY:
        print("\n========= EVENT HISTORY =========")
        for e in EVENT_HISTORY[-50:]:
            print(e)


def main():
    if not API_KEY:
        print("Missing BYNO_API_KEY in .env ...")
        input()
        return

    cfg = read_config() or setup()
    last_prices = {}

    while True:
        k = keypress()
        if k == "m":
            menu(cfg)
        if k == "q":
            return

        interval = max(5, int(cfg.get("intervalSeconds", 30)))
        rows = []

        for it in cfg["items"]:
            name = it["market_hash_name"]
            target = float(it.get("target_tl", 0))

            log_event(f"Checking: {name}")

            price, lid, link, best_listing, err = fetch_lowest_buy_now(name)

            if err and err != "NO_ACTIVE":
                rows.append((name, "-", "-", "no_list"))
                continue

            prev = last_prices.get(name)
            changed = (prev != price) if (prev is not None and price is not None) else False
            hit = (price is not None) and (price <= target) and (err is None)

            status = "ok"
            if err == "NO_ACTIVE":
                status = "no_active"
            elif hit:
                status = "TARGET!"
            elif changed:
                status = "changed"

            rows.append((name, f"{price:.2f}" if price is not None else "-", f"{target:.2f}", status))

            if hit:
                log_event(f"TARGET FOUND {name} {price:.2f} TL")
                if link:
                    log_event(link)
                elif lid:
                    log_event(f"Listing ID: {lid}")
                else:
                    log_event("Listing found but no link/id")

            last_prices[name] = price

        print_ui(rows, interval)

        end = time.time() + interval
        while time.time() < end:
            k = keypress()
            if k == "m":
                menu(cfg)
                break
            if k == "q":
                return
            time.sleep(0.1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("CRASH:", e)

        input()
