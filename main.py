import os
import time
import cloudscraper
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests

# Yükle .env dosyasını
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
AMAZON_URLS = os.getenv("AMAZON_URLS", "")
CHECK_INTERVAL = 15  # saniye
SENT_PRODUCTS = {}

url_list = [url.strip() for url in AMAZON_URLS.split(",") if url.strip()]
scraper = cloudscraper.create_scraper()

def get_headers():
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0) "
            "Gecko/20100101 Firefox/117.0"
        ),
        "Accept-Language": "tr,en-US;q=0.7,en;q=0.3",
    }

def fetch_products(url):
    try:
        response = scraper.get(url, headers=get_headers(), timeout=15)
        if response.status_code != 200:
            print(f"[HATA] Amazon HTTP durumu: {response.status_code}")
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
        response = requests.post(url, data=data, timeout=10)
        if response.status_code != 200:
            print(f"[Telegram Hatası] Status code: {response.status_code}, Yanıt: {response.text}")
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
                        print(f"🆕 Yeni ürün bulundu: {product['title']}")
                        send_telegram_message(product)
                        SENT_PRODUCTS[url].add(product['title'])
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"[Loop Hatası]: {e}")
            time.sleep(20)

if __name__ == "__main__":
    monitor()
