"""
StockSense AI – Backend API
Run locally:  uvicorn main:app --reload
Run Render:   uvicorn main:app --host 0.0.0.0 --port 10000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests

# Load .env if present (local dev). On Render, env vars are injected directly.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="StockSense AI", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Config ───────────────────────────────────────────────────────────────────
STOCK_API_KEY  = os.getenv("STOCK_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
USD_TO_INR     = 83.0

# ─── Stock Mock Database ──────────────────────────────────────────────────────
STOCKS = {
    "AAPL":     {"usd": 189.43, "chg": 1.25,  "name": "Apple Inc.",              "cap": "₹244.8T",    "pe": 28.45, "ex": "NASDAQ"},
    "MSFT":     {"usd": 412.15, "chg": 0.87,  "name": "Microsoft Corp.",          "cap": "₹253.1T",   "pe": 35.20, "ex": "NASDAQ"},
    "NVDA":     {"usd": 875.28, "chg": 3.45,  "name": "NVIDIA Corp.",             "cap": "₹178.5T",   "pe": 72.10, "ex": "NASDAQ"},
    "TSLA":     {"usd": 175.22, "chg": -2.10, "name": "Tesla Inc.",               "cap": "₹46.2T",    "pe": 48.30, "ex": "NASDAQ"},
    "TCS":      {"usd": 44.00,  "chg": 1.10,  "name": "Tata Consultancy Services","cap": "₹15.2L Cr", "pe": 31.20, "ex": "NSE/BSE"},
    "RELIANCE": {"usd": 35.00,  "chg": 0.80,  "name": "Reliance Industries",      "cap": "₹19.8L Cr", "pe": 28.70, "ex": "NSE/BSE"},
    "INFY":     {"usd": 19.00,  "chg": -0.50, "name": "Infosys Ltd.",             "cap": "₹6.1L Cr",  "pe": 23.80, "ex": "NSE/BSE"},
    "HDFCBANK": {"usd": 20.00,  "chg": 1.30,  "name": "HDFC Bank",               "cap": "₹11.5L Cr", "pe": 19.40, "ex": "NSE/BSE"},
    "SBIN":     {"usd": 8.50,   "chg": 2.10,  "name": "State Bank of India",      "cap": "₹7.2L Cr",  "pe": 11.20, "ex": "NSE/BSE"},
    "WIPRO":    {"usd": 6.00,   "chg": -0.80, "name": "Wipro Ltd.",               "cap": "₹2.5L Cr",  "pe": 21.30, "ex": "NSE/BSE"},
    "ITC":      {"usd": 3.50,   "chg": 0.60,  "name": "ITC Ltd.",                "cap": "₹3.4L Cr",  "pe": 27.10, "ex": "NSE/BSE"},
    # Tamil Nadu companies
    "CPCL":     {"usd": 10.00,  "chg": 1.80,  "name": "Chennai Petroleum Corp.", "cap": "₹14,900Cr", "pe": 8.40,  "ex": "NSE/BSE"},
    "TNPL":     {"usd": 4.50,   "chg": 0.90,  "name": "Tamil Nadu Newsprint",    "cap": "₹3,200Cr",  "pe": 14.20, "ex": "NSE/BSE"},
    "RAMCOCEM": {"usd": 9.00,   "chg": 1.20,  "name": "Ramco Cements",           "cap": "₹18,500Cr", "pe": 42.10, "ex": "NSE/BSE"},
    "CGPOWER":  {"usd": 6.50,   "chg": 2.40,  "name": "CG Power & Industrial",  "cap": "₹12,800Cr", "pe": 55.30, "ex": "NSE/BSE"},
    "LAOPALA":  {"usd": 3.00,   "chg": -0.30, "name": "La Opala RG",            "cap": "₹2,100Cr",  "pe": 38.20, "ex": "NSE/BSE"},
    "PCBL":     {"usd": 2.50,   "chg": 1.10,  "name": "PCBL Ltd.",              "cap": "₹4,800Cr",  "pe": 22.10, "ex": "NSE/BSE"},
}

TN_STOCKS = ["CPCL", "TNPL", "RAMCOCEM", "CGPOWER", "LAOPALA", "PCBL"]
KNOWN = {k.lower(): k for k in STOCKS}


def inr(usd): return round(usd * USD_TO_INR, 2)


def build_stock_response(ticker: str) -> dict:
    d = STOCKS.get(ticker, {"usd": 50.0, "chg": 0.5, "name": ticker, "cap": "N/A", "pe": "N/A", "ex": "NSE/BSE"})
    price = inr(d["usd"])
    return {
        "ticker": ticker,
        "current_price": price,
        "current_price_inr": f"₹{price:,.2f}",
        "change_24h": d["chg"],
        "change_amount": round(d["usd"] * abs(d["chg"]) / 100 * USD_TO_INR, 2),
        "company_name": d["name"],
        "market_cap": d["cap"],
        "volume": "N/A",
        "pe_ratio": d["pe"],
        "range_52w": "N/A",
        "exchange": d["ex"],
        "currency": "INR",
    }


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "service": "StockSense AI API v2.0"}


@app.get("/test")
def test():
    return {"message": "Backend is working! StockSense AI is live."}


@app.get("/api/stocks/{ticker}")
def get_stock(ticker: str):
    ticker = ticker.upper().replace(".BSE", "").replace(".NSE", "")
    if STOCK_API_KEY and ticker not in TN_STOCKS:
        try:
            sym = ticker if ticker in ["AAPL", "MSFT", "NVDA", "TSLA"] else f"{ticker}.BSE"
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={sym}&apikey={STOCK_API_KEY}"
            r = requests.get(url, timeout=8).json()
            gq = r.get("Global Quote", {})
            p = float(gq.get("05. price", 0) or 0)
            if p > 0:
                price = inr(p)
                chg = float(gq.get("10. change percent", "0").replace("%", "") or 0)
                d = STOCKS.get(ticker, {})
                return {
                    "ticker": ticker,
                    "current_price": price,
                    "current_price_inr": f"₹{price:,.2f}",
                    "change_24h": round(chg, 2),
                    "change_amount": round(float(gq.get("09. change", 0) or 0) * USD_TO_INR, 2),
                    "company_name": d.get("name", ticker),
                    "market_cap": d.get("cap", "N/A"),
                    "volume": gq.get("06. volume", "N/A"),
                    "pe_ratio": d.get("pe", "N/A"),
                    "range_52w": "N/A",
                    "exchange": d.get("ex", "N/A"),
                    "currency": "INR",
                }
        except Exception:
            pass
    return build_stock_response(ticker)


@app.get("/api/predict/{ticker}")
def predict(ticker: str):
    ticker = ticker.upper()
    trends = ["Bullish", "Bearish", "Neutral"]
    trend = trends[len(ticker) % 3]
    confidence = 72 + (len(ticker) % 20)
    insights = [
        {"type": "positive", "title": "RSI Divergence", "desc": "Upward breakout signal detected."},
        {"type": "positive", "title": "Sentiment Spike", "desc": "High volume of bullish options activity."},
        {"type": "neutral",  "title": "Macro Watch",    "desc": "Monitor broader market conditions."},
    ]
    if trend == "Bearish":
        insights = [{"type": "negative", "title": "MACD Crossover", "desc": "Bearish divergence on daily timeframe."}]
    return {"ticker": ticker, "trend": trend, "confidence": confidence, "insights": insights}


@app.get("/api/watchlist/")
def get_watchlist():
    return ["AAPL", "TCS", "RELIANCE"]


class WatchlistItem(BaseModel):
    ticker: str


@app.post("/api/watchlist/")
def add_watchlist(item: WatchlistItem):
    return {"status": "success", "message": f"{item.ticker.upper()} added to watchlist"}


class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat/")
def chat(data: ChatRequest):
    msg = data.message.lower()

    # Tamil Nadu stocks query
    if any(w in msg for w in ["tamilnadu", "tamil", "chennai", "tn stock"]):
        lines = "\n".join([f"• {STOCKS[t]['name']} ({t}) – ₹{inr(STOCKS[t]['usd']):,.2f}" for t in TN_STOCKS])
        reply = f"📍 Top Tamil Nadu Listed Companies:\n\n{lines}\n\nRamco Cements and CPCL are strong long-term picks."
        if GOOGLE_API_KEY:
            ai_reply = call_gemini(
                "You are StockSense AI. Give a 2-sentence insight on Tamil Nadu-based NSE/BSE listed companies like Ramco Cements, CPCL, TNPL, CG Power. Be concise.",
                GOOGLE_API_KEY
            )
            if ai_reply:
                reply += f"\n\n🤖 AI Insight: {ai_reply}"
        return {"reply": reply}

    # Known stock lookup
    found = None
    for key, sym in KNOWN.items():
        if key in msg:
            found = sym
            break

    if found or any(w in msg for w in ["price", "stock", "invest", "buy", "sell"]):
        sym = found or "TCS"
        d = build_stock_response(sym)
        trend = ["Bullish", "Bearish", "Neutral"][len(sym) % 3]
        conf = 72 + (len(sym) % 20)
        reply = f"📊 {sym} ({STOCKS.get(sym, {}).get('name', sym)})\nPrice: {d['current_price_inr']}\nTrend: {trend} | Confidence: {conf}%"
        if GOOGLE_API_KEY:
            ai_reply = call_gemini(
                f"You are StockSense AI. Give 2 sentences of investment insight for {sym} at ₹{d['current_price']:,.2f}. Mention trend and one key factor. No direct buy/sell advice.",
                GOOGLE_API_KEY
            )
            if ai_reply:
                reply += f"\n\n🤖 {ai_reply}"
        return {"reply": reply}

    # General AI query
    if GOOGLE_API_KEY:
        ai_reply = call_gemini(
            f"You are StockSense AI, an expert in Indian (NSE/BSE) and global markets. Answer in bullet points, use ₹ INR for Indian stocks.\n\nUser: {data.message}",
            GOOGLE_API_KEY
        )
        if ai_reply:
            return {"reply": ai_reply}

    return {"reply": "👋 Ask me: 'TCS price', 'Best Tamil Nadu stocks', 'Is Reliance bullish?', or 'Investment plan ₹50,000'"}


def call_gemini(prompt: str, api_key: str) -> str | None:
    """Call Gemini 2.0 Flash via REST — no SDK dependency."""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        r = requests.post(url, json=body, timeout=15)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"Gemini error: {e}")
        return None
