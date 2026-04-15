"""
utils/price_updater.py — safe version for Streamlit Cloud
yfinance is optional — if not installed, refresh button shows a warning.
"""
import requests
import streamlit as st
import pandas as pd
from datetime import datetime

# ── Check yfinance availability ──────────────────────────────
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

GOLD_PER_GRAM_FALLBACK = 9200.0

NSE_AUTO_MAP = {
    "reliance industries": "RELIANCE.NS", "hdfc bank": "HDFCBANK.NS",
    "infosys": "INFY.NS", "tcs": "TCS.NS", "icici bank": "ICICIBANK.NS",
    "wipro": "WIPRO.NS", "sbi": "SBIN.NS", "state bank of india": "SBIN.NS",
    "axis bank": "AXISBANK.NS", "kotak bank": "KOTAKBANK.NS",
    "bajaj finance": "BAJFINANCE.NS", "larsen & toubro": "LT.NS",
    "titan": "TITAN.NS", "hcl technologies": "HCLTECH.NS",
    "bharti airtel": "BHARTIARTL.NS", "sun pharma": "SUNPHARMA.NS",
    "tata motors": "TATAMOTORS.NS", "tata steel": "TATASTEEL.NS",
    "ongc": "ONGC.NS", "power grid": "POWERGRID.NS", "ntpc": "NTPC.NS",
    "coal india": "COALINDIA.NS", "recltd": "RECLTD.NS",
    "suzlon": "SUZLON.NS", "oilietf": "OILIETF.NS",
    "niftybees": "NIFTYBEES.NS", "nippon nifty bees": "NIFTYBEES.NS",
    "goldbees": "GOLDBEES.NS", "nippon gold etf": "GOLDBEES.NS",
    "hdfc gold etf": "HDFCGOLD.NS", "bankbees": "BANKBEES.NS",
}

MF_AUTO_MAP = {
    "mirae asset large cap": "119551",
    "parag parikh flexi cap": "122639",
    "axis long term equity": "120503",
    "axis bluechip": "120465",
    "hdfc flexi cap": "119062",
    "sbi bluechip": "119598",
    "uti nifty 50": "120716",
    "edelweiss nifty": "147946",
    "edelweiss nlm": "147946",
}

ISIN_SCHEME_MAP = {
    "INF754K01NR9": "147946",  # Edelweiss Nifty LargeMidcap 250
    "INF769K01DM8": "122639",  # Parag Parikh Flexi Cap
    "INF846K01DP8": "120503",  # Axis Long Term Equity
}


def fetch_gold_price_per_gram() -> dict:
    result = {
        "gold_24k_gram": GOLD_PER_GRAM_FALLBACK,
        "gold_22k_gram": round(GOLD_PER_GRAM_FALLBACK * 22/24, 2),
        "source": "fallback",
        "updated_at": datetime.now().strftime("%d %b %Y %H:%M"),
    }
    try:
        r = requests.get("https://metals.live/api/v1/spot/gold", timeout=6)
        if r.status_code == 200:
            usd = float(r.json().get("price", 0))
            if usd > 0:
                fx = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5)
                inr = 84.0
                if fx.status_code == 200:
                    inr = float(fx.json().get("rates", {}).get("INR", 84.0))
                g24 = (usd / 31.1035) * inr
                result.update({"gold_24k_gram": round(g24, 2),
                               "gold_22k_gram": round(g24 * 22/24, 2),
                               "source": "metals.live",
                               "updated_at": datetime.now().strftime("%d %b %Y %H:%M")})
    except Exception:
        pass
    return result


@st.cache_data(ttl=86400)
def isin_to_scheme_code(isin: str):
    isin = isin.strip().upper()
    if isin in ISIN_SCHEME_MAP:
        return ISIN_SCHEME_MAP[isin]
    try:
        r = requests.get(f"https://api.mfapi.in/mf/search?q={isin}", timeout=8)
        if r.status_code == 200:
            results = r.json()
            if results:
                return str(results[0].get("schemeCode", ""))
    except Exception:
        pass
    return None


def fetch_mf_nav(scheme_code: str):
    try:
        r = requests.get(f"https://api.mfapi.in/mf/{scheme_code}", timeout=8)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data:
                return float(data[0].get("nav", 0))
    except Exception:
        pass
    return None


def fetch_stock_price(ticker_symbol: str):
    if not YFINANCE_AVAILABLE:
        return None
    try:
        ticker = yf.Ticker(ticker_symbol)
        price = ticker.fast_info.get("lastPrice") or ticker.fast_info.get("regularMarketPrice")
        if price and float(price) > 0:
            return round(float(price), 2)
        hist = ticker.history(period="2d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        pass
    return None


def _is_isin(s: str) -> bool:
    import re
    return bool(re.match(r'^[A-Z]{2}[A-Z0-9]{10}$', s.strip().upper()))


def resolve_ticker(asset_name, asset_class, category, user_ticker):
    name_lower = asset_name.lower().strip()
    cat_lower  = category.lower()
    if user_ticker and str(user_ticker).strip():
        t = str(user_ticker).strip().upper()
        if _is_isin(t):
            code = isin_to_scheme_code(t)
            if code:
                return code
            return None
        if t.isdigit():
            return t
        if "." in t:
            return t
        return t + ".NS"
    if asset_class == "Equity" or (asset_class == "Gold" and "etf" in cat_lower):
        return NSE_AUTO_MAP.get(name_lower)
    if asset_class == "Mutual Fund":
        for key, code in MF_AUTO_MAP.items():
            if key in name_lower:
                return code
    return None


@st.cache_data(ttl=900)
def fetch_all_prices(asset_list: list, inv_df_json: str) -> dict:
    inv_df  = pd.read_json(inv_df_json, orient="records")
    results = {}
    errors  = {}
    gold    = fetch_gold_price_per_gram()
    g24, g22 = gold["gold_24k_gram"], gold["gold_22k_gram"]

    for asset_name in asset_list:
        rows = inv_df[inv_df["Asset_Name"] == asset_name]
        if rows.empty:
            continue
        row         = rows.iloc[0]
        asset_class = str(row.get("Asset_Class", ""))
        category    = str(row.get("Category", ""))
        user_ticker = str(row.get("Ticker", "")).strip() if "Ticker" in row.index else ""

        if asset_class == "Gold":
            cat_l = category.lower()
            if "etf" in cat_l:
                ticker = resolve_ticker(asset_name, asset_class, category, user_ticker)
                if ticker and not ticker.isdigit():
                    price = fetch_stock_price(ticker)
                    if price:
                        results[asset_name] = price
                        continue
            elif "sgb" in cat_l or "sovereign" in asset_name.lower():
                results[asset_name] = g24
            else:
                results[asset_name] = g22
            continue

        if asset_class == "Mutual Fund":
            ticker = resolve_ticker(asset_name, asset_class, category, user_ticker)
            if ticker and ticker.isdigit():
                nav = fetch_mf_nav(ticker)
                if nav:
                    results[asset_name] = nav
                    continue
            if user_ticker and _is_isin(user_ticker.strip().upper()):
                code = isin_to_scheme_code(user_ticker.strip().upper())
                if code:
                    nav = fetch_mf_nav(code)
                    if nav:
                        results[asset_name] = nav
                        continue
            errors[asset_name] = "No scheme code found"
            continue

        if asset_class == "Equity":
            ticker = resolve_ticker(asset_name, asset_class, category, user_ticker)
            if ticker:
                price = fetch_stock_price(ticker)
                if price:
                    results[asset_name] = price
                    continue
            errors[asset_name] = f"No ticker for '{asset_name}'"
            continue

    return {"prices": results, "gold": gold, "errors": errors,
            "fetched_at": datetime.now().strftime("%d %b %Y %H:%M")}


def update_prices_sheet(sheet_obj, prices: dict):
    if not prices:
        return 0, []
    try:
        ws      = sheet_obj.worksheet("Current_Prices")
        records = ws.get_all_records()
        df      = pd.DataFrame(records)
        updated = 0
        if df.empty or "Asset_Name" not in df.columns:
            rows = [[n, p, datetime.now().strftime("%d %b %Y %H:%M")] for n,p in prices.items()]
            ws.append_rows(rows)
            return len(rows), []
        for asset_name, price in prices.items():
            matches = df[df["Asset_Name"] == asset_name]
            if matches.empty:
                ws.append_row([asset_name, price, datetime.now().strftime("%d %b %Y %H:%M")])
            else:
                row_idx = matches.index[0] + 2
                ws.update_cell(row_idx, 2, price)
                if df.shape[1] >= 3:
                    ws.update_cell(row_idx, 3, datetime.now().strftime("%d %b %Y %H:%M"))
            updated += 1
        return updated, []
    except Exception as e:
        return 0, [str(e)]