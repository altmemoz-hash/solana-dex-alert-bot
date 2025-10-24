# bot.py
import aiohttp, asyncio, json, time

# === CONFIG ===
TELEGRAM_BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID   = "PASTE_YOUR_CHAT_ID_HERE"

POLL_INTERVAL = 40  # seconds
DEX_BASE = "https://api.dexscreener.com"
SEEN = set()

# === FILTERS ===
MIN_LIQUIDITY = 10_000
MIN_MARKETCAP = 20_000
MAX_MARKETCAP = 250_000
CHAIN = "solana"

# --- helpers ---
async def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    async with aiohttp.ClientSession() as s:
        await s.post(url, json=payload)

def passes_filters(p):
    try:
        if p.get("chainId") != CHAIN: return False
        liq = float(p.get("liquidity",{}).get("usd",0) or 0)
        mc  = float(p.get("marketCap",0) or 0)
        if liq < MIN_LIQUIDITY: return False
        if mc < MIN_MARKETCAP or mc > MAX_MARKETCAP: return False
        return True
    except: return False

def format_alert(p, tag):
    base = p.get("baseToken",{}).get("symbol","?")
    quote = p.get("quoteToken",{}).get("symbol","?")
    pair = f"{base}/{quote}"
    price = p.get("priceUsd","?")
    liq = p.get("liquidity",{}).get("usd","?")
    mc = p.get("marketCap","?")
    url = p.get("url","")
    return (
        f"🔥 <b>{tag}</b>\n"
        f"💎 <b>{pair}</b>\n"
        f"💰 Price: ${price}\n"
        f"💧 Liquidity: ${liq}\n"
        f"🏦 Market Cap: ${mc}\n"
        f"🌐 {url}"
    )

async def fetch_json(session, url):
    try:
        async with session.get(url, timeout=20) as r:
            return await r.json()
    except: return None

async def poll_loop():
    global SEEN
    async with aiohttp.ClientSession() as s:
        while True:
            try:
                urls = [
                    f"{DEX_BASE}/latest/dex/trending/5m",
                    f"{DEX_BASE}/token-boosts/latest/v1"
                ]
                results = []
                for u in urls:
                    data = await fetch_json(s,u)
                    if isinstance(data, dict):
                        items = data.get("pairs") or data.get("tokens") or data.get("data") or []
                    else:
                        items = data or []
                    results += items

                for p in results:
                    pid = p.get("pairAddress") or p.get("url")
                    if not pid or pid in SEEN: continue
                    if passes_filters(p):
                        tag = "Trending / Boosted"
                        msg = format_alert(p, tag)
                        await send_telegram(msg)
                        SEEN.add(pid)

                await asyncio.sleep(POLL_INTERVAL)
            except Exception as e:
                print("Error:", e)
                await asyncio.sleep(POLL_INTERVAL)

print("🚀 DexScreener → Telegram bot starting…")
asyncio.run(poll_loop())
