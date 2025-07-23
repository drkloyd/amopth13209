import os
import requests
import time
import socket
import threading
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask

import random

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
AMAZON_URLS = os.getenv("AMAZON_URLS", "")
CHECK_INTERVAL = 60  # saniye, Render için biraz uzun tutmak iyi
SENT_PRODUCTS = {}

url_list = [url.strip() for url in AMAZON_URLS.split(",") if url.strip()]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-A715F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36"
]

def resolve_amazon_ip():
    try:
        ip = socket.gethostbyname("www.amazon.com.tr")
        print(f"Amazon IP: {ip}")
        return ip
    except Exception as e:
        print(f"IP çözümleme hatası: {e}")
        return None

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "close",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        "Host": "www.amazon.com.tr"
    }

def fetch_products(url):
    try:
        resolve_amazon_ip()
        response = requests.get(url, headers=get_headers(), timeout=15)
        if response.status_code != 200:
            print(f"[HATA] HTTP {response.status_code} ile cevap alındı ({url})")
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        products = soup.select(".s-main-slot > div[data-index]:nth-of-type(-n+9)")

        result = []
        for product in products:
            title_tag = product.select_one("h2 span")
            link_tag = product.select_one("a.a-link-normal")
            img_tag = product.select_one("img.s-image")

            if title_tag and link_tag and img_tag:
                title = title_tag.get_text(strip=True)
                link = "https://www.amazon.com.tr" + link_tag.get("href")
                img = img_tag.get("src")
                result.append({
                    "title": title,
                    "link": link,
                    "img": img
                })
        return result

    except Exception as e:
        print(f"[HATA] Ürün alınamadı ({url}): {e}")
        return []

def send_telegram_message(product):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        caption = f"🆕 <b>{product['title']}</b>\n\n<a href='{product['link']}'>Ürün Linki</a>"
        data = {
            "chat_id": CHAT_ID,
            "photo": product['img'],
            "caption": caption,
            "parse_mode": "HTML"
        }
        resp = requests.post(url, data=data, timeout=10)
        if resp.status_code != 200:
            print(f"[Telegram Hatası] Status code: {resp.status_code}, Response: {resp.text}")
    except Exception as e:
        print(f"[Telegram Hatası] {e}")

def monitor():
    global SENT_PRODUCTS
    print("🔍 İzleme başladı.")

    for url in url_list:
        SENT_PRODUCTS[url] = set()
        products = fetch_products(url)
        for p in products:
            send_telegram_message(p)
            SENT_PRODUCTS[url].add(p['title'])

    while True:
        try:
            for url in url_list:
                current_products = fetch_products(url)
                for product in current_products:
                    if product['title'] not in SENT_PRODUCTS[url]:
                        print(f"🆕 Yeni ürün bulundu ({url}): {product['title']}")
                        send_telegram_message(product)
                        SENT_PRODUCTS[url].add(product['title'])
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"[Loop Hatası]: {e}")
            time.sleep(60)

app = Flask(__name__)

@app.route("/")
def home():
    return "Amazon ürün izleyici bot çalışıyor."

if __name__ == "__main__":
    # monitor fonksiyonunu ayrı bir threadde başlat
    t = threading.Thread(target=monitor, daemon=True)
    t.start()

    # Flask web server başlasın (Render için port otomatik atanacak)
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
