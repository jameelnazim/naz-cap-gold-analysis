"""
GIT — Gold Intelligence Terminal
Production Backend v4.0
Deploy on Render via GitHub
"""

import os
import json
import time
import threading
import logging
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ── GLOBAL STATE ─────────────────────────────────────────
CACHE = {}
CACHE_LOCK = threading.Lock()
LAST_REFRESH = None
REFRESH_INTERVAL = 30  # seconds

# ── HISTORICAL ANALOG DATABASE ────────────────────────────
HISTORICAL_ANALOGS = [
    {
        "date": "Mar 2024", "event": "Fed pivot signal + DXY collapse",
        "conditions": {"hawk_range": [30, 45], "dxy_chp": [-1, -0.3]},
        "result_24h": +2.8, "result_72h": +4.2, "confidence": 84,
        "desc": "Fed signalled rate cuts, DXY dropped sharply",
        "gold_direction": "BULLISH"
    },
    {
        "date": "Nov 2023", "event": "CPI miss + yield compression",
        "conditions": {"hawk_range": [35, 50], "y10_chp": [-1.5, -0.5]},
        "result_24h": +1.9, "result_72h": +3.8, "confidence": 76,
        "desc": "CPI came below expectations, yields fell",
        "gold_direction": "BULLISH"
    },
    {
        "date": "Aug 2020", "event": "Negative real yields + weak dollar",
        "conditions": {"hawk_range": [0, 30], "vix_range": [20, 35]},
        "result_24h": +1.4, "result_72h": +3.1, "confidence": 71,
        "desc": "Real yields turned negative, dollar at multi-year low",
        "gold_direction": "BULLISH"
    },
    {
        "date": "Sep 2022", "event": "Hawkish Fed + DXY at 20-year high",
        "conditions": {"hawk_range": [75, 100], "dxy_chp": [0.3, 1.5]},
        "result_24h": -1.8, "result_72h": -3.1, "confidence": 83,
        "desc": "Fed hiked 75bps, DXY surged past 114",
        "gold_direction": "BEARISH"
    },
    {
        "date": "Jun 2023", "event": "Strong NFP + yield spike",
        "conditions": {"hawk_range": [65, 85], "y10_chp": [0.5, 2.0]},
        "result_24h": -1.1, "result_72h": -2.4, "confidence": 71,
        "desc": "Jobs beat expectations heavily, yields spiked",
        "gold_direction": "BEARISH"
    },
    {
        "date": "Feb 2023", "event": "Hot CPI + rate hike expectations surge",
        "conditions": {"hawk_range": [70, 90], "dxy_chp": [0.2, 1.0]},
        "result_24h": -0.9, "result_72h": -1.9, "confidence": 68,
        "desc": "Inflation surprise forced markets to reprice hikes",
        "gold_direction": "BEARISH"
    },
    {
        "date": "Oct 2023", "event": "Mixed macro — pre-FOMC neutral",
        "conditions": {"hawk_range": [45, 60], "vix_range": [16, 22]},
        "result_24h": +0.3, "result_72h": -0.5, "confidence": 55,
        "desc": "Market awaiting Fed decision, mixed signals",
        "gold_direction": "NEUTRAL"
    },
    {
        "date": "Jan 2024", "event": "Range-bound pre-CPI consolidation",
        "conditions": {"hawk_range": [40, 58], "dxy_chp": [-0.2, 0.2]},
        "result_24h": +0.2, "result_72h": +0.6, "confidence": 52,
        "desc": "Gold consolidating ahead of key data releases",
        "gold_direction": "NEUTRAL"
    },
    {
        "date": "Mar 2022", "event": "Ukraine escalation + safe-haven surge",
        "conditions": {"hawk_range": [50, 70], "vix_range": [28, 45]},
        "result_24h": +2.1, "result_72h": +2.8, "confidence": 78,
        "desc": "Geopolitical crisis drove safe-haven demand",
        "gold_direction": "BULLISH"
    },
    {
        "date": "May 2023", "event": "Banking stress + Fed pause",
        "conditions": {"hawk_range": [40, 58], "vix_range": [18, 28]},
        "result_24h": +1.3, "result_72h": +1.8, "confidence": 64,
        "desc": "Regional bank stress, Fed signalled pause",
        "gold_direction": "BULLISH"
    },
]

NEWS_FEEDS = [
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters Money", "https://feeds.reuters.com/reuters/money"),
    ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories"),
    ("Investing.com", "https://www.investing.com/rss/news_301.rss"),
    ("Kitco", "https://www.kitco.com/rss/kitconews.rss"),
    ("Bloomberg Markets", "https://feeds.bloomberg.com/markets/news.rss"),
]

GOLD_KEYWORDS = [
    'gold','xau','silver','bullion','precious metal',
    'fed','federal reserve','fomc','powell','rate cut','rate hike',
    'inflation','cpi','pce','core inflation','deflation',
    'dollar','dxy','treasury','yield','bond',
    'nfp','payroll','employment','jobs','unemployment',
    'gdp','growth','recession','tariff','trade war',
    'geopolit','war','conflict','sanction','central bank',
    'ecb','boe','pboc','boj','reserve','rate decision',
    'ism','pmi','manufacturing','consumer confidence',
]

BULLISH_SIGNALS = [
    'rate cut', 'pivot', 'dovish', 'weaker dollar', 'dxy falls', 'yield drop',
    'inflation eases', 'geopolit', 'war', 'conflict', 'crisis', 'safe haven',
    'gold rises', 'gold surges', 'gold rally', 'fed pause', 'qe',
    'quantitative easing', 'recession fears', 'risk off', 'market crash',
    'banking stress', 'financial crisis', 'uncertainty', 'debt ceiling',
    'negative real yield', 'gold demand', 'central bank buying',
]

BEARISH_SIGNALS = [
    'rate hike', 'hawkish', 'strong dollar', 'dxy rises', 'yield spike',
    'hot cpi', 'inflation surge', 'strong nfp', 'strong jobs', 'tightening',
    'qt', 'quantitative tighten', 'gold falls', 'gold drops', 'gold selloff',
    'risk on', 'strong economy', 'beat expectations', 'better than expected',
    'higher for longer', 'rate hold hawkish', 'dollar strength',
]

# ── DATA IMPORT WITH FALLBACK ─────────────────────────────
def safe_import():
    try:
        import yfinance as yf
        import numpy as np
        import feedparser
        return yf, np, feedparser
    except ImportError as e:
        log.error(f"Import error: {e}")
        return None, None, None

yf, np, feedparser = safe_import()

# ── TECHNICAL INDICATORS ──────────────────────────────────
def calc_rsi(closes, period=14):
    if np is None or len(closes) < period + 2:
        return None
    arr = list(closes)
    gains, losses = [], []
    for i in range(1, len(arr)):
        d = arr[i] - arr[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    if len(gains) < period:
        return None
    ag = float(np.mean(gains[:period]))
    al = float(np.mean(losses[:period]))
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
    if al == 0:
        return 100.0
    return round(100 - (100 / (1 + ag / al)), 2)

def calc_ema(closes, period):
    if np is None or len(closes) < period:
        return None
    arr = list(closes)
    k = 2 / (period + 1)
    ema = float(np.mean(arr[:period]))
    for c in arr[period:]:
        ema = c * k + ema * (1 - k)
    return round(ema, 2)

def calc_vwap(highs, lows, closes, volumes):
    if np is None:
        return None
    tp = (highs + lows + closes) / 3
    vp = tp * volumes
    total = volumes.sum()
    return round(float(vp.sum() / total), 2) if total > 0 else round(float(closes.iloc[-1]), 2)

def calc_atr(highs, lows, closes, period=14):
    if np is None or len(closes) < 2:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            float(highs.iloc[i]) - float(lows.iloc[i]),
            abs(float(highs.iloc[i]) - float(closes.iloc[i-1])),
            abs(float(lows.iloc[i]) - float(closes.iloc[i-1]))
        )
        trs.append(tr)
    subset = trs[-period:] if len(trs) >= period else trs
    return round(float(np.mean(subset)), 2) if subset else None

def calc_structure(highs, lows):
    if len(highs) < 12:
        return {"text": "INSUFFICIENT DATA", "dir": 0}
    rH = max(highs[-6:])
    rL = min(lows[-6:])
    pH = max(highs[-12:-6])
    pL = min(lows[-12:-6])
    if rH > pH and rL > pL:
        return {"text": "BULLISH HH/HL", "dir": 1}
    if rH < pH and rL < pL:
        return {"text": "BEARISH LH/LL", "dir": -1}
    if rH > pH and rL < pL:
        return {"text": "RANGE EXPANSION", "dir": 0}
    return {"text": "CONSOLIDATION", "dir": 0}

def find_fvg(highs, lows):
    gaps = []
    for i in range(2, len(highs)):
        if lows[i] > highs[i-2]:
            gaps.append({"type": "BULL", "lo": round(float(highs[i-2]), 2), "hi": round(float(lows[i]), 2)})
        if highs[i] < lows[i-2]:
            gaps.append({"type": "BEAR", "lo": round(float(highs[i]), 2), "hi": round(float(lows[i-2]), 2)})
    return gaps[-3:] if gaps else []

# ── MARKET DATA FETCHING ──────────────────────────────────
SYMBOLS = {
    "gold":    "GC=F",
    "silver":  "SI=F",
    "copper":  "HG=F",
    "dxy":     "DX-Y.NYB",
    "ten_y":   "^TNX",
    "two_y":   "^IRX",
    "tips":    "TIP",
    "vix":     "^VIX",
    "spx":     "^GSPC",
    "dji":     "^DJI",
    "ndx":     "^IXIC",
    "wti":     "CL=F",
    "ng":      "NG=F",
    "eurusd":  "EURUSD=X",
    "gbpusd":  "GBPUSD=X",
    "usdjpy":  "JPY=X",
    "usdcnh":  "CNH=X",
    "gld":     "GLD",
    "gdx":     "GDX",
    "slv":     "SLV",
}

def fetch_quote(ticker_sym):
    if yf is None:
        return None
    try:
        tk = yf.Ticker(ticker_sym)
        info = tk.fast_info
        price = getattr(info, 'last_price', None) or getattr(info, 'previous_close', None)
        prev = getattr(info, 'previous_close', None) or price
        if not price:
            return None
        price = float(price)
        prev = float(prev) if prev else price
        ch = price - prev
        chp = (ch / prev * 100) if prev != 0 else 0
        return {
            "price": round(price, 4),
            "prev":  round(prev, 4),
            "ch":    round(ch, 4),
            "chp":   round(chp, 4),
            "high":  round(float(getattr(info, 'day_high', price) or price), 4),
            "low":   round(float(getattr(info, 'day_low', price) or price), 4),
        }
    except Exception as e:
        log.warning(f"Quote error {ticker_sym}: {e}")
        return None

def fetch_technicals():
    if yf is None or np is None:
        return {}
    try:
        tk = yf.Ticker("GC=F")
        df5 = tk.history(period="5d", interval="5m")
        dfD  = tk.history(period="60d", interval="1d")
        result = {}

        if not df5.empty:
            closes5 = df5["Close"].dropna()
            highs5  = df5["High"].dropna()
            lows5   = df5["Low"].dropna()
            opens5  = df5["Open"].dropna()
            vols5   = df5["Volume"].fillna(1)
            cur = float(closes5.iloc[-1])
            result["cur"]   = round(cur, 2)
            result["rsi"]   = calc_rsi(closes5.values, 14)
            result["ema20"] = calc_ema(closes5.values, min(20, len(closes5)-1))
            result["ema50"] = calc_ema(closes5.values, min(50, len(closes5)-1))

            today_mask = df5.index.date == df5.index[-1].date()
            today = df5[today_mask]
            if len(today) > 3:
                result["vwap"]         = calc_vwap(today["High"], today["Low"], today["Close"], today["Volume"].fillna(1))
                result["session_high"] = round(float(today["High"].max()), 2)
                result["session_low"]  = round(float(today["Low"].min()), 2)
                result["today_open"]   = round(float(today["Open"].iloc[0]), 2)
            else:
                result["vwap"]         = round(cur, 2)
                result["session_high"] = round(float(highs5.iloc[-1]), 2)
                result["session_low"]  = round(float(lows5.iloc[-1]), 2)
                result["today_open"]   = round(cur, 2)

            if len(highs5) >= 12:
                result["structure_5m"] = calc_structure(highs5.values.tolist(), lows5.values.tolist())
            result["fvg"]   = find_fvg(highs5.values.tolist(), lows5.values.tolist())
            result["atr_5m"] = calc_atr(highs5, lows5, closes5, 14)

        if not dfD.empty:
            closesD = dfD["Close"].dropna()
            highsD  = dfD["High"].dropna()
            lowsD   = dfD["Low"].dropna()

            result["ema200"]    = calc_ema(closesD.values, min(200, len(closesD)-1))
            result["atr_daily"] = calc_atr(highsD, lowsD, closesD, 14)

            if len(dfD) >= 2:
                result["pdh"] = round(float(dfD["High"].iloc[-2]), 2)
                result["pdl"] = round(float(dfD["Low"].iloc[-2]), 2)
            if len(dfD) >= 7:
                result["pwh"] = round(float(dfD["High"].iloc[-7:].max()), 2)
                result["pwl"] = round(float(dfD["Low"].iloc[-7:].min()), 2)
            if len(dfD) >= 30:
                result["pmh"] = round(float(dfD["High"].iloc[-30:].max()), 2)
                result["pml"] = round(float(dfD["Low"].iloc[-30:].min()), 2)

            if len(highsD) >= 12:
                result["structure_d"] = calc_structure(highsD.values.tolist(), lowsD.values.tolist())

            if len(closesD) >= 20:
                e20d  = calc_ema(closesD.values, 20)
                e50d  = calc_ema(closesD.values, min(50, len(closesD)-1))
                cur_d = float(closesD.iloc[-1])
                rH10  = float(highsD.iloc[-10:].max())
                rL10  = float(lowsD.iloc[-10:].min())
                pH10  = float(highsD.iloc[-20:-10].max()) if len(highsD) >= 20 else rH10
                pL10  = float(lowsD.iloc[-20:-10].min()) if len(lowsD) >= 20 else rL10
                recent_rng = rH10 - rL10
                prev_rng   = pH10 - pL10
                if recent_rng < prev_rng * 0.45:
                    result["phase"] = "ACCUMULATION"
                elif e20d and e50d and e20d > e50d and cur_d > e20d:
                    result["phase"] = "EXPANSION"
                elif e20d and e50d and e20d < e50d and cur_d < e20d:
                    result["phase"] = "DISTRIBUTION"
                else:
                    result["phase"] = "REVERSAL WATCH"

        return result
    except Exception as e:
        log.error(f"Technicals error: {e}")
        return {}

# ── NEWS FETCHING + CLASSIFICATION ───────────────────────
def classify_news(title, summary=""):
    text = (title + " " + summary).lower()
    if not any(k in text for k in GOLD_KEYWORDS):
        return None
    bull = sum(1 for k in BULLISH_SIGNALS if k in text)
    bear = sum(1 for k in BEARISH_SIGNALS if k in text)
    if bull > bear:
        return {"dir": 1,  "label": "BULLISH GOLD", "channel": _get_channel(text, "bull")}
    elif bear > bull:
        return {"dir": -1, "label": "BEARISH GOLD", "channel": _get_channel(text, "bear")}
    return {"dir": 0, "label": "MONITOR", "channel": "Watch for transmission"}

def _get_channel(text, side):
    if "yield" in text or "treasury" in text or "bond" in text:
        return "Real yield channel"
    if "dollar" in text or "dxy" in text or "usd" in text:
        return "USD inverse channel"
    if "inflation" in text or "cpi" in text or "pce" in text:
        return "Inflation expectations"
    if "war" in text or "geopolit" in text or "conflict" in text or "sanction" in text:
        return "Safe-haven demand"
    if "fed" in text or "rate" in text or "fomc" in text:
        return "Rate expectation repricing"
    if "risk" in text or "vix" in text or "crisis" in text:
        return "Risk sentiment channel"
    return "Macro sentiment"

def historical_match(text):
    text_l = text.lower()
    matches = []
    if any(k in text_l for k in ["rate cut","pivot","dovish","fed pause","qe"]):
        matches.append(HISTORICAL_ANALOGS[0])
        matches.append(HISTORICAL_ANALOGS[9])
    if any(k in text_l for k in ["cpi","inflation","pce","core"]):
        matches.append(HISTORICAL_ANALOGS[1])
        matches.append(HISTORICAL_ANALOGS[5])
    if any(k in text_l for k in ["war","geopolit","conflict","sanction","crisis"]):
        matches.append(HISTORICAL_ANALOGS[8])
        matches.append(HISTORICAL_ANALOGS[2])
    if any(k in text_l for k in ["hawkish","rate hike","tighten","higher for longer"]):
        matches.append(HISTORICAL_ANALOGS[3])
        matches.append(HISTORICAL_ANALOGS[5])
    if any(k in text_l for k in ["nfp","payroll","employment","jobs","unemployment"]):
        matches.append(HISTORICAL_ANALOGS[4])
    if not matches:
        matches = [HISTORICAL_ANALOGS[6], HISTORICAL_ANALOGS[7]]
    seen = set()
    unique = []
    for m in matches:
        k = m["date"]
        if k not in seen:
            seen.add(k)
            unique.append(m)
    return unique[:3]

def fetch_news():
    if feedparser is None:
        return []
    items = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; GoldTerminal/4.0)"}
    for source_name, url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(url, request_headers=headers)
            for entry in feed.entries[:12]:
                title   = entry.get("title", "").strip()
                summary = entry.get("summary", "")[:300]
                pub     = entry.get("published", "")
                link    = entry.get("link", "#")
                if not title:
                    continue
                impact = classify_news(title, summary)
                if impact is None:
                    continue
                analogs = historical_match(title + " " + summary)
                items.append({
                    "title":   title[:130],
                    "summary": summary[:200],
                    "time":    pub,
                    "link":    link,
                    "source":  source_name,
                    "impact":  impact,
                    "analogs": analogs[:2],
                })
        except Exception as e:
            log.warning(f"News error {source_name}: {e}")
            continue
    # Deduplicate
    seen, unique = set(), []
    for item in items:
        k = item["title"][:50]
        if k not in seen:
            seen.add(k)
            unique.append(item)
    return unique[:15]

# ── SCORING ENGINES ───────────────────────────────────────
def calc_hawkish_index(market):
    h = 50
    ten = market.get("ten_y") or {}
    two = market.get("two_y") or {}
    dxy = market.get("dxy") or {}
    tips = market.get("tips") or {}

    t10p  = ten.get("price", 4.2)
    t10cp = ten.get("chp", 0)
    t2p   = two.get("price", 4.6)
    dxyp  = dxy.get("price", 103)
    dxcp  = dxy.get("chp", 0)
    ticp  = tips.get("chp", 0)

    if t10p > 4.5:   h += 15
    elif t10p > 4.0: h += 8
    elif t10p < 3.5: h -= 12
    if t10cp > 0.5:  h += 8
    elif t10cp < -0.5: h -= 8
    if t2p > 4.8:    h += 10
    elif t2p < 4.0:  h -= 8
    if dxyp > 104:   h += 7
    elif dxyp < 101: h -= 7
    if dxcp > 0.3:   h += 5
    elif dxcp < -0.3: h -= 5
    if ticp < -0.2:  h += 6
    elif ticp > 0.2: h -= 6

    return int(max(0, min(100, h)))

def hawk_regime(h):
    if h <= 20:  return "DOVISH EXPANSION",    -1
    if h <= 40:  return "DISINFLATION PHASE",  -1
    if h <= 60:  return "NEUTRAL REGIME",       0
    if h <= 80:  return "HAWKISH TIGHTENING",   1
    return             "INFLATION SHOCK",        1

def calc_fedwatch(market):
    ten  = market.get("ten_y") or {}
    two  = market.get("two_y") or {}
    t10p = ten.get("price", 4.2)
    t2p  = two.get("price", 4.6)
    t10c = ten.get("chp", 0)
    sp   = t10p - t2p
    cut, hold, hike = 30, 55, 15
    if sp < -0.5:   cut, hold, hike = 52, 36, 12
    elif sp > 0.3:  cut, hold, hike = 18, 45, 37
    if t10c < -0.5: cut += 10; hike -= 5
    elif t10c > 0.5: cut -= 10; hike += 10
    total = cut + hold + hike
    return {
        "cut":  round(cut / total * 100),
        "hold": round(hold / total * 100),
        "hike": round(hike / total * 100),
    }

def calc_macro_score(market, hawk):
    s = 50
    reasons = []
    dxy   = market.get("dxy") or {}
    ten   = market.get("ten_y") or {}
    tips  = market.get("tips") or {}
    vix   = market.get("vix") or {}
    spx   = market.get("spx") or {}
    wti   = market.get("wti") or {}
    silver= market.get("silver") or {}

    dxcp  = dxy.get("chp", 0)
    t10cp = ten.get("chp", 0)
    tipcp = tips.get("chp", 0)
    vixp  = vix.get("price", 18)
    vixcp = vix.get("chp", 0)
    spxcp = spx.get("chp", 0)
    wticp = wti.get("chp", 0)

    if dxcp < -0.5:   s += 16; reasons.append({"d": 1,  "t": f"DXY down {abs(dxcp):.2f}% — dollar weakness, gold's primary tailwind"})
    elif dxcp < -0.2: s += 8;  reasons.append({"d": 1,  "t": f"DXY -{ abs(dxcp):.2f}% — mild dollar softness supporting XAU"})
    elif dxcp > 0.5:  s -= 16; reasons.append({"d": -1, "t": f"DXY +{dxcp:.2f}% — dollar strength, direct XAU headwind"})
    elif dxcp > 0.2:  s -= 8;  reasons.append({"d": -1, "t": f"DXY +{dxcp:.2f}% — mild dollar pressure on gold"})
    else:             reasons.append({"d": 0,  "t": f"DXY flat ({dxcp:+.2f}%) — neutral currency environment"})

    if t10cp < -1:    s += 14; reasons.append({"d": 1,  "t": f"10Y falling sharply {t10cp:+.2f}% — real yield compression, strong gold bid"})
    elif t10cp < -0.3: s += 7; reasons.append({"d": 1,  "t": f"10Y easing {t10cp:+.2f}% — favorable real yield dynamics"})
    elif t10cp > 1:   s -= 14; reasons.append({"d": -1, "t": f"10Y surging +{t10cp:.2f}% — rising opportunity cost crushes XAU"})
    elif t10cp > 0.3: s -= 7;  reasons.append({"d": -1, "t": f"10Y +{t10cp:.2f}% — yield pressure building"})

    if tipcp > 0.15:  s += 9;  reasons.append({"d": 1,  "t": f"TIPS ETF bid +{tipcp:.2f}% — real yields compressing"})
    elif tipcp < -0.15: s -= 9; reasons.append({"d": -1, "t": f"TIPS selling {tipcp:+.2f}% — real yields rising"})

    if vixp > 28:     s += 12; reasons.append({"d": 1,  "t": f"VIX {vixp:.1f} — extreme fear, institutional safe-haven surge"})
    elif vixp > 20 and vixcp > 5: s += 6; reasons.append({"d": 1, "t": f"VIX spiking +{vixcp:.1f}% — risk-off building"})
    elif vixp < 14:   s -= 7;  reasons.append({"d": -1, "t": f"VIX {vixp:.1f} — complacency, risk-on reduces gold demand"})

    if spxcp < -1:    s += 8;  reasons.append({"d": 1,  "t": f"S&P -{abs(spxcp):.2f}% — equity selloff driving safe-haven rotation"})
    elif spxcp > 1:   s -= 6;  reasons.append({"d": -1, "t": f"S&P +{spxcp:.2f}% — risk appetite reducing gold demand"})

    if wticp > 2:     s += 6;  reasons.append({"d": 1,  "t": f"WTI +{wticp:.2f}% — inflation expectations rising"})
    elif wticp < -2:  s -= 4;  reasons.append({"d": -1, "t": f"WTI {wticp:+.2f}% — deflationary signal"})

    if hawk > 65:     s -= 6;  reasons.append({"d": -1, "t": f"Hawkish Index {hawk} — tightening regime unfavorable for gold"})
    elif hawk < 35:   s += 6;  reasons.append({"d": 1,  "t": f"Hawkish Index {hawk} — dovish regime supportive for gold"})

    return int(max(5, min(95, s))), reasons

def calc_tech_score(tech):
    if not tech:
        return 50, []
    s = 50
    reasons = []
    rsi  = tech.get("rsi")
    e20  = tech.get("ema20")
    e50  = tech.get("ema50")
    e200 = tech.get("ema200")
    vwap = tech.get("vwap")
    cur  = tech.get("cur")
    pdh  = tech.get("pdh")
    pdl  = tech.get("pdl")
    str5 = tech.get("structure_5m", {})
    fvgs = tech.get("fvg", [])

    if rsi is not None:
        if rsi > 55 and rsi < 70:  s += 12; reasons.append({"d": 1,  "t": f"RSI {rsi:.1f} — bullish momentum, room to extend"})
        elif rsi >= 70:            s += 3;  reasons.append({"d": 0,  "t": f"RSI {rsi:.1f} — overbought, watch for exhaustion"})
        elif rsi < 45 and rsi > 30:s -= 12; reasons.append({"d": -1, "t": f"RSI {rsi:.1f} — bearish momentum dominating"})
        elif rsi <= 30:            s += 5;  reasons.append({"d": 0,  "t": f"RSI {rsi:.1f} — oversold, reversal watch active"})
        else:                      reasons.append({"d": 0,  "t": f"RSI {rsi:.1f} — neutral momentum zone"})

    if vwap and cur:
        d = 1 if cur > vwap else -1
        s += d * 10
        reasons.append({"d": d, "t": f"Price {'above' if d > 0 else 'below'} VWAP ${vwap:,.2f} — institutional {'bulls' if d > 0 else 'bears'} in control"})

    if e20 and cur:
        s += 6 if cur > e20 else -6
    if e50 and cur:
        d = 1 if cur > e50 else -1; s += d * 7
        reasons.append({"d": d, "t": f"Price {'above' if d > 0 else 'below'} EMA50 ${e50:,.2f} — {'uptrend intact' if d > 0 else 'downtrend structure'}"})
    if e200 and cur:
        d = 1 if cur > e200 else -1; s += d * 5
        reasons.append({"d": d, "t": f"Price {'above' if d > 0 else 'below'} EMA200 — {'macro bull trend' if d > 0 else 'macro bear trend'}"})

    if str5.get("dir"):
        d = str5["dir"]; s += d * 8
        if d != 0:
            reasons.append({"d": d, "t": f"5M structure: {str5.get('text')} — timeframe bias {'bullish' if d > 0 else 'bearish'}"})

    if pdh and pdl and cur:
        if cur > pdh:   s += 10; reasons.append({"d": 1,  "t": f"Price above PDH ${pdh:,.2f} — buy-side liquidity swept"})
        elif cur < pdl: s -= 10; reasons.append({"d": -1, "t": f"Price below PDL ${pdl:,.2f} — sell-side liquidity taken"})
        else:
            mid = (pdh + pdl) / 2; s += 4 if cur > mid else -4

    if fvgs:
        f = fvgs[-1]; d = 1 if f["type"] == "BULL" else -1; s += d * 4

    return int(max(5, min(95, s))), reasons

def find_best_analogs(hawk, macro_s, tech_s, market):
    comp = round(macro_s * 0.5 + tech_s * 0.5)
    matches = []
    for a in HISTORICAL_ANALOGS:
        score = 0
        hr = a["conditions"].get("hawk_range", [0, 100])
        if hr[0] <= hawk <= hr[1]:
            score += 35
        if comp >= 62 and a["gold_direction"] == "BULLISH":
            score += 30
        elif comp <= 38 and a["gold_direction"] == "BEARISH":
            score += 30
        elif 38 < comp < 62 and a["gold_direction"] == "NEUTRAL":
            score += 20
        dxy = market.get("dxy") or {}
        dxcp = dxy.get("chp", 0)
        dc = a["conditions"].get("dxy_chp", [-99, 99])
        if dc[0] <= dxcp <= dc[1]:
            score += 20
        vix = market.get("vix") or {}
        vp = vix.get("price", 18)
        vr = a["conditions"].get("vix_range", [0, 99])
        if vr[0] <= vp <= vr[1]:
            score += 15
        if score > 0:
            matches.append({**a, "match_score": min(95, score + 20)})
    matches.sort(key=lambda x: x["match_score"], reverse=True)
    return matches[:3]

# ── BACKGROUND REFRESH ────────────────────────────────────
def refresh_data():
    global LAST_REFRESH
    log.info("Refreshing all market data...")
    market = {}
    for key, sym in SYMBOLS.items():
        q = fetch_quote(sym)
        if q:
            market[key] = q
        time.sleep(0.1)

    tech   = fetch_technicals()
    news   = fetch_news()
    hawk   = calc_hawkish_index(market)
    fw     = calc_fedwatch(market)
    macro_s, macro_r = calc_macro_score(market, hawk)
    tech_s,  tech_r  = calc_tech_score(tech)
    comp   = round(macro_s * 0.5 + tech_s * 0.5)
    analogs= find_best_analogs(hawk, macro_s, tech_s, market)
    regime, regime_dir = hawk_regime(hawk)

    all_reasons = macro_r + tech_r
    bull_c = sum(1 for r in all_reasons if r["d"] > 0)
    bear_c = sum(1 for r in all_reasons if r["d"] < 0)
    total  = len(all_reasons) or 1
    align  = abs(bull_c - bear_c) / total
    confidence = int(min(95, max(30, 38 + align * 57 + abs(comp - 50) * 0.35)))

    gold_p = (market.get("gold") or {}).get("price", 0)
    silver_p = (market.get("silver") or {}).get("price", 1)
    gsr = round(gold_p / silver_p, 2) if silver_p else None

    payload = {
        "market":      market,
        "tech":        tech,
        "news":        news,
        "hawk":        hawk,
        "hawk_regime": regime,
        "hawk_dir":    regime_dir,
        "fedwatch":    fw,
        "macro_score": macro_s,
        "macro_reasons": macro_r,
        "tech_score":  tech_s,
        "tech_reasons": tech_r,
        "composite":   comp,
        "confidence":  confidence,
        "reasons":     all_reasons[:10],
        "analogs":     analogs,
        "gsr":         gsr,
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "status":      "live",
    }

    with CACHE_LOCK:
        CACHE["data"] = payload
    LAST_REFRESH = time.time()
    gold_price = (market.get("gold") or {}).get("price", "N/A")
    log.info(f"Refresh complete — Gold: ${gold_price} | Composite: {comp}/100 | Confidence: {confidence}%")

def background_loop():
    time.sleep(3)
    while True:
        try:
            refresh_data()
        except Exception as e:
            log.error(f"Background refresh error: {e}")
        time.sleep(REFRESH_INTERVAL)

# ── ROUTES ────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/all")
def api_all():
    with CACHE_LOCK:
        data = CACHE.get("data")
    if not data:
        if not data:
    return jsonify({
        "status": "warming_up",
        "market": {},
        "message": "System initializing. Data will appear shortly."
    }), 200

@app.route("/api/health")
def health():
    with CACHE_LOCK:
        has_data = "data" in CACHE
    return jsonify({
        "status": "ok",
        "data_ready": has_data,
        "last_refresh": LAST_REFRESH,
        "server": "GIT v4.0"
    })

# ── STARTUP ───────────────────────────────────────────────
def start_background():
    t = threading.Thread(target=background_loop, daemon=True)
    t.start()
    log.info("Background data thread started")

start_background()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
