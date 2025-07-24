import os
import requests
import time
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
AMAZON_URLS = os.getenv("AMAZON_URLS", "")
CHECK_INTERVAL = 5
ASIN_FILE = "sent_asins.txt"

# Kayıtlı ASIN'leri yükle
SENT_ASINS = set()
if os.path.exists(ASIN_FILE):
    with open(ASIN_FILE, "r") as f:
        SENT_ASINS = set(line.strip() for line in f)

url_list = [url.strip() for url in AMAZON_URLS.split(",") if url.strip()]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8"
}

def extract_asin_from_url(url):
    if "/dp/" in url:
        return url.split("/dp/")[1].split("/")[0].split("?")[0]
    elif "/gp/product/" in url:
        return url.split("/gp/product/")[1].split("/")[0].split("?")[0]
    return None

def fetch_products(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select("div[data-asin][data-index]:nth-of-type(-n+10)")

        new_products = []
        for item in items:
            asin = item.get("data-asin", "").strip()
            if not asin or asin in SENT_ASINS:
                continue

            link_tag = item.select_one("a.a-link-normal[href*='/dp/']")
            title_tag = item.select_one("h2 span")
            img_tag = item.select_one("img.s-image")
            price_tag = item.select_one("span.a-price-whole")

            if not (link_tag and title_tag and img_tag):
                continue

            title = title_tag.text.strip()
            link = "https://www.amazon.com.tr" + link_tag["href"].split("?")[0]
            img = img_tag["src"]
            price = price_tag.text.strip() if price_tag else "Fiyat yok"
            try:
                price_float = float(price.replace(".", "").replace(",", "."))
                price = f"{int(price_float)} TL"
            except:
                price = price + " TL"

            new_products.append({
                "asin": asin,
                "title": title,
                "link": link,
                "img": img,
                "price": price
            })
        return new_products

    except Exception as e:
        print(f"[HATA] Ürün alınamadı: {e}")
        return []

def send_telegram(product):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        caption = (
            f"🆕 <b>{product['title']}</b>\n"
            f"💰 <b>Fiyat:</b> {product['price']}\n"
            f"\n🔗 <a href='{product['link']}'>Ürüne Git</a>"
        )
        data = {
            "chat_id": CHAT_ID,
            "photo": product["img"],
            "caption": caption,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data, timeout=10)
        if response.status_code != 200:
            print(f"[Telegram Hatası] {response.text}")
    except Exception as e:
        print(f"[Telegram Hatası] {e}")

def save_asin(asin):
    SENT_ASINS.add(asin)
    with open(ASIN_FILE, "a") as f:
        f.write(f"{asin}\n")

def monitor():
    print("🚀 Ürün izleme başladı...")
    while True:
        for url in url_list:
            products = fetch_products(url)
            for product in products:
                print(f"🆕 Yeni ürün bulundu: {product['title']}")
                send_telegram(product)
                save_asin(product["asin"])
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    monitor()
