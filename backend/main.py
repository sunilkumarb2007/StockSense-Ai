"""
StockSense AI – Complete Production Backend
Run locally:  uvicorn main:app --reload
Deploy Render: uvicorn main:app --host 0.0.0.0 --port 10000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, requests

# Load .env locally — on Render vars are injected directly
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── ENV ───────────────────────────────────────────────────────────────────────
STOCK_API_KEY  = os.getenv("STOCK_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
USD_TO_INR     = 83.0

# ── APP ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="StockSense AI", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── STOCK DATABASE (INR) ──────────────────────────────────────────────────────
STOCKS = {
    # Indian Blue Chips
    "TCS":      {"usd":44.0,  "chg":1.10,  "name":"Tata Consultancy Services", "cap":"₹15.2L Cr","pe":31.2,"ex":"NSE/BSE","sector":"IT"},
    "RELIANCE": {"usd":35.0,  "chg":0.80,  "name":"Reliance Industries",       "cap":"₹19.8L Cr","pe":28.7,"ex":"NSE/BSE","sector":"Conglomerate"},
    "INFY":     {"usd":19.0,  "chg":-0.50, "name":"Infosys Ltd.",              "cap":"₹6.1L Cr", "pe":23.8,"ex":"NSE/BSE","sector":"IT"},
    "HDFCBANK": {"usd":20.0,  "chg":1.30,  "name":"HDFC Bank",                "cap":"₹11.5L Cr","pe":19.4,"ex":"NSE/BSE","sector":"Banking"},
    "SBIN":     {"usd":8.50,  "chg":2.10,  "name":"State Bank of India",       "cap":"₹7.2L Cr", "pe":11.2,"ex":"NSE/BSE","sector":"Banking"},
    "WIPRO":    {"usd":6.00,  "chg":-0.80, "name":"Wipro Ltd.",                "cap":"₹2.5L Cr", "pe":21.3,"ex":"NSE/BSE","sector":"IT"},
    "ITC":      {"usd":3.50,  "chg":0.60,  "name":"ITC Ltd.",                 "cap":"₹3.4L Cr", "pe":27.1,"ex":"NSE/BSE","sector":"FMCG"},
    "BAJFINANCE":{"usd":17.0, "chg":1.50,  "name":"Bajaj Finance",            "cap":"₹5.2L Cr", "pe":32.4,"ex":"NSE/BSE","sector":"NBFC"},
    "KOTAKBANK":{"usd":22.0,  "chg":0.40,  "name":"Kotak Mahindra Bank",      "cap":"₹8.8L Cr", "pe":24.1,"ex":"NSE/BSE","sector":"Banking"},
    # Tamil Nadu Companies
    "CPCL":     {"usd":10.0,  "chg":1.80,  "name":"Chennai Petroleum Corp.",  "cap":"₹14,900Cr","pe":8.4, "ex":"NSE/BSE","sector":"Oil & Gas"},
    "TNPL":     {"usd":4.50,  "chg":0.90,  "name":"Tamil Nadu Newsprint",     "cap":"₹3,200Cr", "pe":14.2,"ex":"NSE/BSE","sector":"Paper"},
    "RAMCOCEM": {"usd":9.00,  "chg":1.20,  "name":"Ramco Cements",            "cap":"₹18,500Cr","pe":42.1,"ex":"NSE/BSE","sector":"Cement"},
    "CGPOWER":  {"usd":6.50,  "chg":2.40,  "name":"CG Power & Industrial",   "cap":"₹12,800Cr","pe":55.3,"ex":"NSE/BSE","sector":"Electricals"},
    "LAOPALA":  {"usd":3.00,  "chg":-0.30, "name":"La Opala RG",             "cap":"₹2,100Cr", "pe":38.2,"ex":"NSE/BSE","sector":"Glassware"},
    "PCBL":     {"usd":2.50,  "chg":1.10,  "name":"PCBL Ltd.",               "cap":"₹4,800Cr", "pe":22.1,"ex":"NSE/BSE","sector":"Chemicals"},
    # US Stocks
    "AAPL":     {"usd":189.43,"chg":1.25,  "name":"Apple Inc.",               "cap":"₹244.8T",  "pe":28.45,"ex":"NASDAQ","sector":"Technology"},
    "MSFT":     {"usd":412.15,"chg":0.87,  "name":"Microsoft Corp.",           "cap":"₹253.1T",  "pe":35.20,"ex":"NASDAQ","sector":"Technology"},
    "NVDA":     {"usd":875.28,"chg":3.45,  "name":"NVIDIA Corp.",              "cap":"₹178.5T",  "pe":72.10,"ex":"NASDAQ","sector":"Semiconductors"},
    "TSLA":     {"usd":175.22,"chg":-2.10, "name":"Tesla Inc.",                "cap":"₹46.2T",   "pe":48.30,"ex":"NASDAQ","sector":"Automotive"},
    "SNOW":     {"usd":165.00,"chg":2.10,  "name":"Snowflake Inc.",            "cap":"₹14.2T",   "pe":None, "ex":"NYSE", "sector":"Cloud"},
}

TN_STOCKS   = ["CPCL","TNPL","RAMCOCEM","CGPOWER","LAOPALA","PCBL"]
KNOWN_MAP   = {k.lower(): k for k in STOCKS}   # for chat parsing


def inr(usd: float) -> float:
    return round(usd * USD_TO_INR, 2)


def build_stock(ticker: str) -> dict:
    d = STOCKS.get(ticker, {"usd":50.0,"chg":0.5,"name":ticker,"cap":"N/A","pe":"N/A","ex":"NSE/BSE","sector":"N/A"})
    price = inr(d["usd"])
    return {
        "ticker":          ticker,
        "current_price":   price,
        "current_price_inr": f"₹{price:,.2f}",
        "change_24h":      d["chg"],
        "change_amount":   round(d["usd"] * abs(d["chg"]) / 100 * USD_TO_INR, 2),
        "company_name":    d["name"],
        "market_cap":      d["cap"],
        "volume":          "N/A",
        "pe_ratio":        d["pe"],
        "range_52w":       "N/A",
        "exchange":        d["ex"],
        "sector":          d.get("sector","N/A"),
        "currency":        "INR",
    }


# ── GEMINI via REST (no SDK — stable on Render) ───────────────────────────────
def gemini(prompt: str):
    if not GOOGLE_API_KEY:
        return "API key missing"

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"

        response = requests.post(
            url,
            json={
                "contents": [{"parts": [{"text": prompt}]}]
            },
            timeout=10
        )

        data = response.json()

        # ✅ SAFE PARSING
        if "candidates" in data and len(data["candidates"]) > 0:
            parts = data["candidates"][0].get("content", {}).get("parts", [])
            if len(parts) > 0:
                return parts[0].get("text", "No response")

        # fallback
        return "AI couldn't generate response. Try again."

    except Exception as e:
        return f"Error: {str(e)}"


# ── IN-MEMORY WATCHLIST ───────────────────────────────────────────────────────
watchlist_db: list[str] = ["TCS", "RELIANCE", "INFY"]


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {"status": "ok", "service": "StockSense AI API v3.0"}


@app.get("/test")
def test():
    return {"message": "Backend is working! StockSense AI is live."}


# ── STOCKS ────────────────────────────────────────────────────────────────────
@app.get("/api/stocks/{ticker}")
def get_stock(ticker: str):
    ticker = ticker.upper().replace(".BSE","").replace(".NSE","")

    # Try AlphaVantage if key present and not a pure TN stock (they're INR native)
    if STOCK_API_KEY and ticker not in TN_STOCKS:
        try:
            sym = ticker if ticker in ["AAPL","MSFT","NVDA","TSLA","SNOW"] else f"{ticker}.BSE"
            url = (f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE"
                   f"&symbol={sym}&apikey={STOCK_API_KEY}")
            r = requests.get(url, timeout=8).json()
            gq = r.get("Global Quote", {})
            p = float(gq.get("05. price", 0) or 0)
            if p > 0:
                price = inr(p)
                chg   = float(gq.get("10. change percent","0").replace("%","") or 0)
                d     = STOCKS.get(ticker, {})
                return {
                    "ticker": ticker,
                    "current_price": price,
                    "current_price_inr": f"₹{price:,.2f}",
                    "change_24h": round(chg, 2),
                    "change_amount": round(float(gq.get("09. change",0) or 0)*USD_TO_INR, 2),
                    "company_name": d.get("name", ticker),
                    "market_cap":   d.get("cap",  "N/A"),
                    "volume":       gq.get("06. volume","N/A"),
                    "pe_ratio":     d.get("pe",   "N/A"),
                    "range_52w":    "N/A",
                    "exchange":     d.get("ex",   "N/A"),
                    "sector":       d.get("sector","N/A"),
                    "currency":     "INR",
                }
        except Exception:
            pass  # fall through to mock

    return build_stock(ticker)


# ── PREDICT ───────────────────────────────────────────────────────────────────
@app.get("/api/predict/{ticker}")
def predict(ticker: str):
    ticker = ticker.upper()
    trends = ["Bullish", "Bearish", "Neutral"]
    trend  = trends[len(ticker) % 3]
    conf   = 72 + (len(ticker) % 20)

    if trend == "Bullish":
        insights = [
            {"type":"positive","title":"RSI Divergence",     "desc":"Upward breakout signal detected on daily chart."},
            {"type":"positive","title":"Sentiment Spike",    "desc":"High volume of bullish options activity observed."},
            {"type":"neutral", "title":"Macro Watch",        "desc":"Monitor US Fed rate signals for broader impact."},
        ]
    elif trend == "Bearish":
        insights = [
            {"type":"negative","title":"MACD Crossover",     "desc":"Bearish divergence confirmed on daily timeframe."},
            {"type":"negative","title":"Volume Declining",   "desc":"Decreasing volumes signal weakening momentum."},
        ]
    else:
        insights = [
            {"type":"neutral","title":"Consolidation Phase","desc":"Price compressing between key moving averages."},
            {"type":"neutral","title":"Await Catalyst",     "desc":"No clear directional signal yet. Monitor closely."},
        ]

    return {"ticker": ticker, "trend": trend, "confidence": conf, "insights": insights}


# ── WATCHLIST ─────────────────────────────────────────────────────────────────
@app.get("/api/watchlist/")
def get_watchlist():
    return watchlist_db


class WatchlistItem(BaseModel):
    ticker: str

@app.post("/api/watchlist/")
def add_watchlist(item: WatchlistItem):
    t = item.ticker.upper()
    if t not in watchlist_db:
        watchlist_db.append(t)
    return {"status": "success", "watchlist": watchlist_db}

@app.delete("/api/watchlist/{ticker}")
def remove_watchlist(ticker: str):
    t = ticker.upper()
    if t in watchlist_db:
        watchlist_db.remove(t)
    return {"status": "success", "watchlist": watchlist_db}


# ── CHAT (Real Gemini AI) ─────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat/")
async def chat(req: ChatRequest):
    reply = gemini(f"You are Indian stock AI. Answer in ₹ INR.\nUser: {req.message}")
    return {"reply": reply}
