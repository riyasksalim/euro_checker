import asyncio
from playwright.async_api import async_playwright
import requests
import re
from collections import defaultdict

TELEGRAM_TOKEN = "8122891534:AAG-RrC8Pn8ZRyT7yY_2gBCe9iTeWQCZJjg"
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
GET_UPDATES_URL = f"{API_URL}/getUpdates"
SEND_MESSAGE_URL = f"{API_URL}/sendMessage"

# Store per-user config
user_thresholds = {}
user_delays = {}

# Fetch updates from users
def fetch_user_settings():
    try:
        response = requests.get(GET_UPDATES_URL)
        data = response.json()

        if not data.get("ok"):
            print("⚠️ Error fetching updates.")
            return

        for update in data["result"]:
            message = update.get("message", {})
            chat = message.get("chat", {})
            user_id = str(chat.get("id"))
            text = message.get("text", "").strip()

            if not user_id or not text:
                continue

            if match := re.match(r"INR:(\d+(\.\d+)?)", text):
                threshold = float(match.group(1))
                user_thresholds[user_id] = threshold
                print(f"💾 Set threshold {threshold} for {user_id}")

            elif match := re.match(r"DELAY:(\d+)", text):
                delay = int(match.group(1))
                user_delays[user_id] = delay
                print(f"💾 Set delay {delay}s for {user_id}")

    except Exception as e:
        print(f"❌ Error during getUpdates: {e}")

# Send Telegram message
def send_telegram_message(user_id, rate, threshold):
    message = f"💱 Alert! 1 EUR = {rate} INR (Your threshold {threshold} was crossed)"
    payload = {
        "chat_id": user_id,
        "text": message
    }

    try:
        response = requests.post(SEND_MESSAGE_URL, data=payload)
        if response.status_code == 200:
            print(f"✅ Message sent to {user_id}")
        else:
            print(f"❌ Failed for {user_id}: {response.text}")
    except Exception as e:
        print(f"❌ Telegram error for {user_id}: {e}")

# Playwright logic to fetch the rate
async def get_current_exchange_rate(playwright):
    try:
        browser = await playwright.chromium.launch(headless=True, args=["--start-maximized"])
        context = await browser.new_context(viewport=None)
        page = await context.new_page()

        await page.goto("https://www.monito.com/en/compare/transfer/de/in/eur/inr/1000")
        await page.wait_for_timeout(3000)
        rate_text = await page.locator("span.lg\\:text-18.font-semibold").first.text_content()
        clean_text = rate_text.strip()
        rate_value = float(clean_text.split('=')[1].strip().split()[0])
        print(f"🌐 Current EUR → INR Rate: {rate_value}")
        await browser.close()
        return rate_value

    except Exception as e:
        print(f"❌ Error in browser: {e}")
        return None

# Main async loop
async def main():
    async with async_playwright() as playwright:
        while True:
            fetch_user_settings()

            # Only check rate if we have valid users
            valid_users = [uid for uid in user_thresholds if uid in user_delays]
            if not valid_users:
                print("ℹ️ No users configured with both INR and DELAY.")
                await asyncio.sleep(5)
                continue

            rate = await get_current_exchange_rate(playwright)
            if rate is None:
                await asyncio.sleep(5)
                continue

            # Send alerts only to users who configured both
            for user_id in valid_users:
                threshold = user_thresholds[user_id]
                delay = user_delays[user_id]

                if rate >= threshold:
                    send_telegram_message(user_id, rate, threshold)
                else:
                    print(f"📉 Rate {rate} is below threshold {threshold} for {user_id}")

            # Use shortest delay across all users
            min_delay = min(user_delays.values())
            await asyncio.sleep(min_delay)

# Run the script
asyncio.run(main())
