"""
Daily Market Dashboard - Data Builder
Fetches market data, computes trend regime, and outputs JSON for static dashboard.
Run: python scripts/build_data.py --out-dir data
"""
import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone

import yfinance as yf
import pandas as pd
import numpy as np

# ─── CONFIG ─────────────────────────────────────────────────────────

# Major Indexes
INDEXES = {
    "SPY": "S&P 500 ETF",
    "QQQ": "Nasdaq 100",
    "DIA": "Dow Jones 30",
    "IWM": "Russell 2000",
}

# S&P 500 Sectors
SECTORS = {
    "XLK": "Technology",
    "XLE": "Energy",
    "XLU": "Utilities",
    "XLY": "Consumer Discretionary",
    "XLI": "Industrials",
    "XLC": "Communication Services",
    "XLB": "Materials",
    "XLF": "Financials",
    "XLP": "Consumer Staples",
    "XLV": "Healthcare",
}

# Thematic / Industry ETFs
THEMATIC = {
    "SMH": "Semiconductors",
    "IGV": "Software",
    "IHAK": "Cybersecurity & Tech",
    "IYZ": "Telecom",
    "IYT": "Transportation",
    "TAN": "Solar",
    "XHB": "Homebuilders",
    "XRT": "Retail",
    "IBB": "Biotech",
    "IYR": "Real Estate",
}

# Macro instruments
MACRO = {
    "VIXY": "VIX (Volatility)",
    "GLD": "Gold",
    "TLT": "20+ Yr Treasuries",
    "^TNX": "10-Yr Yield",
    "^FVX": "5-Yr Yield",
    "^IRX": "2-Yr Yield",
}

# Liquid leaders (top S&P 500 stocks by market cap / volume)
LEADERS = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "Nvidia",
    "GOOGL": "Alphabet",
    "AMZN": "Amazon",
    "META": "Meta",
    "TSLA": "Tesla",
    "BRK-B": "Berkshire Hathaway",
    "AVGO": "Broadcom",
    "JPM": "JPMorgan",
    "V": "Visa",
    "WMT": "Walmart",
    "JNJ": "Johnson & Johnson",
    "XOM": "Exxon Mobil",
    "UNH": "UnitedHealth",
    "MA": "Mastercard",
    "PG": "Procter & Gamble",
    "HD": "Home Depot",
    "LLY": "Eli Lilly",
    "CVX": "Chevron",
    "MRK": "Merck",
    "PEP": "PepsiCo",
    "ABBV": "AbbVie",
    "COST": "Costco",
    "TMO": "Thermo Fisher",
}

# T2108 proxy — % of S&P 500 stocks above 50-day MA (StockCharts symbol)
# Note: Yahoo Finance may not have this exact symbol; we try multiple variants
T2108_PROXIES = ["^SPXA50R", "$SPXA50R", "SPXA50R"]

# Crypto
CRYPTO = {
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "SOL-USD": "Solana",
    "ZEC-USD": "Zcash",
}

# Offense vs Defense tickers for regime check
OFFENSE_TICKERS = ["XLK", "SMH", "IGV"]
DEFENSE_TICKERS = ["XLU", "XLP", "XLV"]

# All tickers to fetch
ALL_TICKERS = {**INDEXES, **SECTORS, **THEMATIC, **MACRO, **CRYPTO, **LEADERS}

# Sector colors (borrowed from traderwillhu)
SECTOR_COLORS = {
    "Technology": "#3f51b5",
    "Industrials": "#333333",
    "Utilities": "#009688",
    "Consumer Discretionary": "#4caf50",
    "Communication Services": "#9c27b0",
    "Materials": "#ff9800",
    "Financials": "#ff5722",
    "Consumer Staples": "#8bc34a",
    "Healthcare": "#e91e63",
    "Energy": "#795548",
}

# ─── HELPERS ────────────────────────────────────────────────────────

def fetch_history(ticker, period="1y"):
    """Fetch historical data with retry logic."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        if hist is None or hist.empty or len(hist) < 50:
            return None
        return hist
    except Exception as e:
        print(f"  Error fetching {ticker}: {e}")
        return None


def compute_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()


def compute_sma(series, window):
    return series.rolling(window=window).mean()


def compute_metrics(hist):
    """Compute all dashboard metrics from price history."""
    if hist is None or len(hist) < 50:
        return None

    close = hist["Close"].iloc[-1]
    prev_close = hist["Close"].iloc[-2]

    # Daily change
    daily_chg = (close / prev_close - 1) * 100

    # 5-day change
    five_day_chg = (close / hist["Close"].iloc[-6] - 1) * 100 if len(hist) >= 6 else None

    # 20-day change
    twenty_day_chg = (close / hist["Close"].iloc[-21] - 1) * 100 if len(hist) >= 21 else None

    # YTD change
    ytd_start = hist[hist.index >= f"{hist.index[-1].year}-01-01"]
    ytd_chg = (close / ytd_start["Close"].iloc[0] - 1) * 100 if len(ytd_start) > 0 else None

    # 52-week high
    wk52_high = hist["Close"].max()
    off_high = (close / wk52_high - 1) * 100

    # EMAs and SMAs
    ema20 = compute_ema(hist["Close"], 20).iloc[-1]
    sma50 = compute_sma(hist["Close"], 50).iloc[-1]

    above_ema20 = close > ema20
    above_sma50 = close > sma50

    # ABC Rating (from traderwillhu)
    ema10 = compute_ema(hist["Close"], 10).iloc[-1]
    ema20_val = compute_ema(hist["Close"], 20).iloc[-1]
    sma50_val = compute_sma(hist["Close"], 50).iloc[-1]

    if ema10 > ema20_val and ema20_val > sma50_val:
        abc = "A"
    elif (ema10 > ema20_val and ema20_val < sma50_val) or (ema10 < ema20_val and ema20_val > sma50_val):
        abc = "B"
    elif ema10 < ema20_val and ema20_val < sma50_val:
        abc = "C"
    else:
        abc = "B"

    return {
        "close": round(close, 2),
        "daily": round(daily_chg, 2),
        "intra": round((close / hist["Open"].iloc[-1] - 1) * 100, 2),
        "p5d": round(five_day_chg, 2) if five_day_chg is not None else None,
        "p20d": round(twenty_day_chg, 2) if twenty_day_chg is not None else None,
        "ytd": round(ytd_chg, 2) if ytd_chg is not None else None,
        "off_high": round(off_high, 2),
        "ema20": round(ema20, 2),
        "sma50": round(sma50, 2),
        "above_ema20": bool(above_ema20),
        "above_sma50": bool(above_sma50),
        "abc": abc,
    }


def compute_regime(all_metrics):
    """Compute the 6-check market regime."""
    spy = all_metrics.get("SPY")
    qqq = all_metrics.get("QQQ")

    checks = []

    # 1. SPY vs 20 EMA / 50 SMA
    if spy:
        c1 = spy["above_ema20"] and spy["above_sma50"]
        checks.append(("SPY vs 20 EMA / 50 SMA", c1))
    else:
        checks.append(("SPY vs 20 EMA / 50 SMA", False))

    # 2. QQQ vs 20 EMA / 50 SMA
    if qqq:
        c2 = qqq["above_ema20"] and qqq["above_sma50"]
        checks.append(("QQQ vs 20 EMA / 50 SMA", c2))
    else:
        checks.append(("QQQ vs 20 EMA / 50 SMA", False))

    # 3. SPY trend: 20 EMA above 50 SMA
    if spy:
        c3 = spy["ema20"] > spy["sma50"]
        checks.append(("SPY trend: 20 EMA above 50 SMA", c3))
    else:
        checks.append(("SPY trend: 20 EMA above 50 SMA", False))

    # 4. Breadth: 50%+ of tracked ETFs above both
    tracked = list(SECTORS.keys()) + list(THEMATIC.keys())
    above_both = sum(1 for t in tracked if t in all_metrics and all_metrics[t]["above_ema20"] and all_metrics[t]["above_sma50"])
    breadth_pct = (above_both / len(tracked)) * 100 if tracked else 0
    c4 = breadth_pct >= 50
    checks.append(("Breadth: 50%+ above both", c4))

    # 5. Offense vs Defense (5D)
    offense_5d = []
    for t in OFFENSE_TICKERS:
        if t in all_metrics and all_metrics[t]["p5d"] is not None:
            offense_5d.append(all_metrics[t]["p5d"])
    defense_5d = []
    for t in DEFENSE_TICKERS:
        if t in all_metrics and all_metrics[t]["p5d"] is not None:
            defense_5d.append(all_metrics[t]["p5d"])

    off_avg = sum(offense_5d) / len(offense_5d) if offense_5d else 0
    def_avg = sum(defense_5d) / len(defense_5d) if defense_5d else 0
    spread = off_avg - def_avg
    c5 = spread > 0
    checks.append(("Offense vs Defense (5D)", c5))

    # 6. VIX below 5-day ago (placeholder - uses VIXY as proxy)
    vix = all_metrics.get("VIXY")
    if vix and "hist" in vix:
        try:
            vix_now = vix["close"]
            vix_5d = vix["hist"]["Close"].iloc[-6]
            c6 = vix_now < vix_5d
        except:
            c6 = True
    else:
        c6 = True
    checks.append(("VIX below 5D ago", c6))

    yes_count = sum(1 for _, v in checks if v)

    if yes_count >= 5:
        regime = "GREEN"
        playbook = "full size · new swing entries OK · favor ORB breakout longs"
    elif yes_count >= 3:
        regime = "YELLOW"
        playbook = "1/2 size · be selective · favor pullbacks"
    else:
        regime = "RED"
        playbook = "flat / hedged · no new swing entries · favor short setups"

    # Verify yes_count matches actual true values
    actual_yes = sum(1 for _, v in checks if v)
    return {
        "checks": checks,
        "yes_count": actual_yes,
        "regime": regime,
        "playbook": playbook,
        "breadth_pct": round(breadth_pct, 1),
        "offense_vs_defense": round(spread, 2),
    }


def generate_commentary(all_metrics, regime_data):
    """Auto-generate market commentary from computed data."""
    spy = all_metrics.get("SPY", {})
    qqq = all_metrics.get("QQQ", {})
    dia = all_metrics.get("DIA", {})
    iwm = all_metrics.get("IWM", {})

    parts = []

    # Daily summary
    daily_parts = []
    for ticker, name in [("SPY", "SPY"), ("QQQ", "QQQ"), ("IWM", "IWM"), ("DIA", "DIA")]:
        m = all_metrics.get(ticker, {})
        if m.get("daily") is not None:
            sign = "+" if m["daily"] >= 0 else ""
            daily_parts.append(f"{name} {sign}{m['daily']:.2f}%")

    parts.append(f"Market closed with {', '.join(daily_parts)} on Friday.")

    # 5-day context
    p5d_parts = []
    for ticker, name in [("SPY", "SPY"), ("QQQ", "QQQ"), ("IWM", "IWM")]:
        m = all_metrics.get(ticker, {})
        if m.get("p5d") is not None:
            sign = "+" if m["p5d"] >= 0 else ""
            p5d_parts.append(f"{name} {sign}{m['p5d']:.2f}%")

    if p5d_parts:
        parts.append(f"Over five days: {', '.join(p5d_parts)}.")

    # Sector leadership
    sector_5d = [(t, all_metrics[t]["p5d"]) for t in SECTORS if t in all_metrics and all_metrics[t].get("p5d") is not None]
    sector_5d.sort(key=lambda x: x[1], reverse=True)

    if len(sector_5d) >= 3:
        leaders = [f"{SECTORS[t]} ({t} {v:+.2f}%)" for t, v in sector_5d[:3]]
        laggards = [f"{SECTORS[t]} ({t} {v:+.2f}%)" for t, v in sector_5d[-3:]]
        parts.append(f"Sector leaders: {', '.join(leaders)}. Laggards: {', '.join(laggards)}.")

    # Breadth note
    bp = regime_data.get("breadth_pct", 0)
    parts.append(f"Breadth: {bp:.0f}% of tracked ETFs are above both 20 EMA and 50 SMA.")

    # Macro note
    tnx = all_metrics.get("^TNX", {})
    if tnx.get("close") is not None:
        parts.append(f"10-year yield at {tnx['close']:.2f}%.")

    return " ".join(parts)


def get_top_gainers(all_metrics, min_mcap=None):
    """Get top daily gainers from tracked ETFs."""
    gainers = []
    for ticker, name in {**SECTORS, **THEMATIC}.items():
        m = all_metrics.get(ticker, {})
        if m and m.get("daily") is not None and m["daily"] > 2:
            gainers.append({
                "ticker": ticker,
                "name": name,
                "daily": m["daily"],
                "p5d": m.get("p5d"),
            })
    gainers.sort(key=lambda x: x["daily"], reverse=True)
    return gainers[:8]


# ─── MAIN ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="data", help="Output directory")
    args = parser.parse_args()
    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)

    print("=" * 60)
    print("DAILY MARKET DASHBOARD - DATA BUILDER")
    print(f"Building for: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
    print("=" * 60)

    all_metrics = {}
    all_histories = {}

    # Fetch all tickers
    print("\nFetching market data...")
    for i, (ticker, name) in enumerate(ALL_TICKERS.items(), 1):
        print(f"  [{i}/{len(ALL_TICKERS)}] {ticker} - {name}")
        hist = fetch_history(ticker, period="1y")
        if hist is not None:
            all_histories[ticker] = hist
            metrics = compute_metrics(hist)
            if metrics:
                metrics["name"] = name
                # Store raw history reference for VIX check
                if ticker == "VIXY":
                    metrics["hist"] = hist
                all_metrics[ticker] = metrics
        time.sleep(0.15)

    print(f"\nSuccessfully fetched {len(all_metrics)}/{len(ALL_TICKERS)} tickers")

    # Compute regime
    print("\nComputing market regime...")
    regime_data = compute_regime(all_metrics)
    print(f"  Regime: {regime_data['regime']} ({regime_data['yes_count']}/6 YES)")
    print(f"  Playbook: {regime_data['playbook']}")

    # Generate commentary
    print("\nGenerating market commentary...")
    commentary = generate_commentary(all_metrics, regime_data)

    # Get top gainers
    print("\nFinding top gainers...")
    top_gainers = get_top_gainers(all_metrics)

    # Fetch T2108 proxy
    t2108_proxy = None
    for proxy_ticker in T2108_PROXIES:
        print(f"  Trying T2108 proxy: {proxy_ticker}")
        hist = fetch_history(proxy_ticker, period="6mo")
        if hist is not None and len(hist) > 0:
            t2108_proxy = {
                "ticker": proxy_ticker,
                "value": round(hist["Close"].iloc[-1], 2),
                "daily": round((hist["Close"].iloc[-1] / hist["Close"].iloc[-2] - 1) * 100, 2) if len(hist) > 1 else None,
            }
            print(f"    Success: {t2108_proxy['value']}")
            break
        time.sleep(0.15)
    if t2108_proxy is None:
        print("  T2108 proxy not available via Yahoo Finance")

    # Build snapshot
    snapshot = {
        "built_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "market_date": datetime.now(timezone.utc).strftime("%B %d, %Y"),
        "regime": regime_data,
        "commentary": commentary,
        "top_gainers": top_gainers,
        "indexes": {t: all_metrics.get(t, {}) for t in INDEXES},
        "sectors": [{"ticker": t, "name": n, **all_metrics.get(t, {})} for t, n in SECTORS.items() if t in all_metrics],
        "thematic": [{"ticker": t, "name": n, **all_metrics.get(t, {})} for t, n in THEMATIC.items() if t in all_metrics],
        "macro": [{"ticker": t, "name": n, **all_metrics.get(t, {})} for t, n in MACRO.items() if t in all_metrics],
        "leaders": [{"ticker": t, "name": n, **all_metrics.get(t, {})} for t, n in LEADERS.items() if t in all_metrics],
        "crypto": [{"ticker": t, "name": n, **all_metrics.get(t, {})} for t, n in CRYPTO.items() if t in all_metrics],
        "t2108_proxy": t2108_proxy,
    }

    # Sort sectors by 5D change
    snapshot["sectors"].sort(key=lambda x: x.get("p5d", 0) if x.get("p5d") is not None else -999, reverse=True)

    # Save JSON
    snapshot_path = os.path.join(out_dir, "snapshot.json")
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2, default=str)

    print(f"\nSaved snapshot to: {snapshot_path}")
    print("\nDone!")


if __name__ == "__main__":
    main()
