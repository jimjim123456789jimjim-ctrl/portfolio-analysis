"""
Portfolio Analyser — Powered by Google Gemini (FREE)
=====================================================
• Fetches live NSE stock data via yfinance
• Fetches Mutual Fund NAV via mfapi.in (free, no key)
• Google Gemini Flash does ALL analysis → BUY / HOLD / SELL
• Sends rich HTML report to Gmail (readable on phone)
• Optional Telegram alert

SETUP
-----
1.  pip install yfinance requests google-genai
2.  Set environment variables in PowerShell:
      $env:GEMINI_API_KEY    = "AIzaSy..."
      $env:GMAIL_USER        = "you@gmail.com"
      $env:GMAIL_APP_PASSWORD= "abcdabcdabcdabcd"
      $env:NOTIFY_EMAIL      = "you@gmail.com"
3.  python portfolio_analyser.py
"""

import os, sys, smtplib, datetime, time, logging
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText

# Fix Windows terminal Unicode encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import yfinance as yf
# Suppress yfinance/urllib noisy error logs to stderr
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

import requests
import google.genai as genai

from email_login import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GMAIL_USER,
    GMAIL_APP_PASSWORD,
    NOTIFY_EMAIL,
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID,
    LOOKBACK_DAYS,
    validate_config,
)

# ──────────────────────────────────────────────────────────────
#  YOUR STOCK PORTFOLIO  (your code → NSE ticker, display name)
# ──────────────────────────────────────────────────────────────
MY_STOCKS = {
    "EXIIND":  ("EXIDEIND.NS",   "Exide Industries"),
    "HDFBAN":  ("HDFCBANK.NS",   "HDFC Bank"),
    "ICIBAN":  ("ICICIBANK.NS",  "ICICI Bank"),
    "STABAN":  ("SBIN.NS",       "State Bank of India"),
    "YESBAN":  ("YESBANK.NS",    "Yes Bank"),
    "GOLDEX":  ("GOLDBEES.NS",   "Nippon Gold ETF"),
    "NIPSIL":  ("SILVERBEES.NS", "Nippon Silver ETF"),
    "SRSLIM":  ("SHRIRAMFIN.NS", "Shriram Finance"),
    "HCLTEC":  ("HCLTECH.NS",    "HCL Technologies"),
    "INFTEC":  ("INFY.NS",       "Infosys"),
    "TCS":     ("TCS.NS",        "Tata Consultancy Services"),
    "RELINF":  ("RELIANCE.NS",   "Reliance Industries"),
    "LIC":     ("LICI.NS",       "LIC of India"),
    "ADAGRE":  ("ADANIGREEN.NS", "Adani Green Energy"),
    "ADAPOW":  ("ADANIPOWER.NS", "Adani Power"),
    "INDOIL":  ("IOC.NS",        "Indian Oil Corporation"),
}

# ──────────────────────────────────────────────────────────────
#  YOUR MUTUAL FUNDS  (key → mfapi scheme code, display name)
# ──────────────────────────────────────────────────────────────
MY_MF = {
    "ICICI_LARGECAP":    (120586, "ICICI Pru Large Cap Fund - Growth"),
    "HDFC_MIDCAP_G":     (119062, "HDFC Mid Cap Fund - Growth"),
    "HDFC_MIDCAP_IDCW":  (119065, "HDFC Mid Cap Fund - IDCW"),
    "HSBC_MIDCAP":       (145552, "HSBC Midcap Fund - IDCW"),
    "AXIS_MULTICAP":     (120841, "Axis Multicap Fund - Regular Growth"),
    "ICICI_INFRA":       (120505, "ICICI Pru Infrastructure Fund - Growth"),
    "FRANKLIN_SMALL":    (118989, "Franklin India Small Cap Fund - Growth"),
    "HSBC_VALUE":        (145547, "HSBC Value Fund - Growth"),
    "ICICI_VALUE":       (120578, "ICICI Pru Value Discovery Fund - Growth"),
    "NIPPON_GOLD_FOF":   (118701, "Nippon India Gold Savings Fund - Growth"),
    "NIPPON_SILVER_FOF": (149645, "Nippon India Silver ETF FOF - Growth"),
    "NAVI_NIFTY50":      (145920, "Navi Nifty 50 Index Fund - Regular Growth"),
}

# ──────────────────────────────────────────────────────────────
#  WATCHLIST — Gemini will screen these and pick best BUYs
# ──────────────────────────────────────────────────────────────
WATCHLIST_STOCKS = [
    ("BAJFINANCE.NS",  "Bajaj Finance"),
    ("MARUTI.NS",      "Maruti Suzuki"),
    ("SUNPHARMA.NS",   "Sun Pharma"),
    ("TITAN.NS",       "Titan Company"),
    ("KOTAKBANK.NS",   "Kotak Mahindra Bank"),
    ("HINDUNILVR.NS",  "Hindustan Unilever"),
    ("LT.NS",          "Larsen & Toubro"),
    ("ULTRACEMCO.NS",  "UltraTech Cement"),
    ("ASIANPAINT.NS",  "Asian Paints"),
    ("WIPRO.NS",       "Wipro"),
    ("TATAMOTORS.NS",  "Tata Motors"),
    ("BAJAJFINSV.NS",  "Bajaj Finserv"),
    ("NTPC.NS",        "NTPC"),
    ("POWERGRID.NS",   "Power Grid"),
    ("NESTLEIND.NS",   "Nestle India"),
]

WATCHLIST_MF = [
    (118825, "Axis Bluechip Fund - Growth"),
    (120828, "Parag Parikh Flexi Cap Fund - Growth"),
    (118701, "SBI Small Cap Fund - Growth"),
    (120503, "Kotak Emerging Equity Fund - Growth"),
    (145400, "Quant Small Cap Fund - Growth"),
]

WATCHLIST_ETF = [
    ("NIFTYBEES.NS",  "Nippon Nifty BeES ETF"),
    ("JUNIORBEES.NS", "Nippon Junior BeES ETF"),
    ("BANKBEES.NS",   "Nippon Bank BeES ETF"),
    ("MOM100.NS",     "Motilal Oswal Momentum 100 ETF"),
    ("SETFNIF50.NS",  "SBI Nifty 50 ETF"),
]


# ══════════════════════════════════════════════════════════════
#  DATA FETCHING
# ══════════════════════════════════════════════════════════════

def compute_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    deltas   = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains    = [d for d in deltas[-period:] if d > 0]
    losses   = [-d for d in deltas[-period:] if d < 0]
    avg_gain = sum(gains)  / period if gains  else 0.0
    avg_loss = sum(losses) / period if losses else 0.0
    if avg_loss == 0:
        return 100.0
    return round(100 - 100 / (1 + avg_gain / avg_loss), 1)


def fetch_stock_summary(ticker_ns: str, display_name: str) -> str:
    try:
        # Suppress any yfinance stderr chatter during download
        import contextlib, io
        with contextlib.redirect_stderr(io.StringIO()):
            tk   = yf.Ticker(ticker_ns)
            hist = tk.history(period=f"{LOOKBACK_DAYS}d")

        if hist is None or hist.empty:
            return f"{display_name} ({ticker_ns}): No price data - skipped"

        closes  = hist["Close"].round(2).tolist()
        volumes = hist["Volume"].astype(int).tolist()

        # info can fail for some tickers - handle gracefully
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                info = tk.info
        except Exception:
            info = {}

        cur   = closes[-1]
        p30   = closes[-30] if len(closes) >= 30 else closes[0]
        p90   = closes[0]
        ch30  = round((cur - p30) / p30 * 100, 2)
        ch90  = round((cur - p90) / p90 * 100, 2)
        rsi   = compute_rsi(closes)
        sma20 = round(sum(closes[-20:]) / min(20, len(closes)), 2)
        sma50 = round(sum(closes[-50:]) / min(50, len(closes)), 2)
        avgv  = int(sum(volumes[-20:]) / min(20, len(volumes)))

        return (
            f"Name: {display_name} ({ticker_ns})\n"
            f"Sector: {info.get('sector','N/A')}\n"
            f"Current price: Rs.{cur}\n"
            f"30-day change: {ch30}%  |  90-day change: {ch90}%\n"
            f"52w High: Rs.{info.get('fiftyTwoWeekHigh','N/A')}  "
            f"Low: Rs.{info.get('fiftyTwoWeekLow','N/A')}\n"
            f"PE ratio: {info.get('trailingPE','N/A')}  |  "
            f"Market cap: {info.get('marketCap','N/A')}\n"
            f"RSI(14): {rsi}  |  SMA20: Rs.{sma20}  SMA50: Rs.{sma50}\n"
            f"Avg volume 20d: {avgv:,}\n"
            f"Last 10 closes: {closes[-10:]}"
        )
    except Exception as e:
        # Return a note but do NOT crash — script continues with other tickers
        short_err = str(e).split('\n')[0][:80]
        return f"{display_name} ({ticker_ns}): Skipped - {short_err}"


def fetch_mf_summary(scheme_code: int, display_name: str) -> str:
    try:
        url  = f"https://api.mfapi.in/mf/{scheme_code}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        navs = data.get("data", [])[:90]
        if not navs:
            return f"{display_name}: No NAV data"

        vals = [float(n["nav"]) for n in navs if n.get("nav") not in ("", None)]
        vals.reverse()   # oldest → newest

        cur  = vals[-1]
        p30  = vals[-30] if len(vals) >= 30 else vals[0]
        p90  = vals[0]
        ch30 = round((cur - p30) / p30 * 100, 2)
        ch90 = round((cur - p90) / p90 * 100, 2)
        rsi  = compute_rsi(vals)

        return (
            f"Name: {display_name} (Scheme {scheme_code})\n"
            f"Type: Mutual Fund\n"
            f"Current NAV: Rs.{cur}\n"
            f"30-day change: {ch30}%  |  90-day change: {ch90}%\n"
            f"90d High NAV: Rs.{round(max(vals),2)}  "
            f"Low NAV: Rs.{round(min(vals),2)}\n"
            f"RSI(14) on NAV: {rsi}\n"
            f"Last 10 NAVs: {[round(v,2) for v in vals[-10:]]}"
        )
    except Exception as e:
        return f"{display_name} (Scheme {scheme_code}): Error - {e}"


def fetch_all_data():
    print("\n[1/5] Fetching your stock portfolio...")
    stock_data = {}
    for code, (ticker, name) in MY_STOCKS.items():
        stock_data[code] = fetch_stock_summary(ticker, name)
        print(f"  ✓ {code} ({ticker})")

    print("\n[2/5] Fetching your mutual fund NAVs...")
    mf_data = {}
    for key, (scheme, name) in MY_MF.items():
        mf_data[key] = fetch_mf_summary(scheme, name)
        print(f"  ✓ {key}")
        time.sleep(0.3)

    print("\n[3/5] Fetching watchlist data...")
    wl_stocks, wl_mf, wl_etf = {}, {}, {}

    for ticker, name in WATCHLIST_STOCKS:
        wl_stocks[name] = fetch_stock_summary(ticker, name)
        print(f"  ✓ {name}")

    for scheme, name in WATCHLIST_MF:
        wl_mf[name] = fetch_mf_summary(scheme, name)
        print(f"  ✓ {name}")
        time.sleep(0.3)

    for ticker, name in WATCHLIST_ETF:
        wl_etf[name] = fetch_stock_summary(ticker, name)
        print(f"  ✓ {name}")

    return stock_data, mf_data, wl_stocks, wl_mf, wl_etf


# ══════════════════════════════════════════════════════════════
#  GEMINI ANALYSIS
# ══════════════════════════════════════════════════════════════

def block(d: dict) -> str:
    return "\n\n".join(f"--- {k} ---\n{v}" for k, v in d.items())


def build_prompt(stock_data, mf_data, wl_stocks, wl_mf, wl_etf) -> str:
    today = datetime.date.today().strftime("%d %B %Y")
    return f"""
You are an expert Indian stock market and mutual fund analyst.
Today: {today}

Analyse the portfolio data below. Give BUY / HOLD / SELL for every
portfolio item. For watchlist, only list genuine BUY opportunities.

OUTPUT FORMAT — use EXACTLY this pipe-separated format:

## PORTFOLIO STOCKS
CODE | SIGNAL | Reason (max 15 words)

## PORTFOLIO MUTUAL FUNDS
KEY | SIGNAL | Reason (max 15 words)

## WATCHLIST - STOCK PICKS (BUY only, skip HOLD/SELL)
NAME | BUY | Reason (max 15 words)

## WATCHLIST - MF PICKS (BUY only, skip HOLD/SELL)
NAME | BUY | Reason (max 15 words)

## WATCHLIST - ETF PICKS (BUY only, skip HOLD/SELL)
NAME | BUY | Reason (max 15 words)

## MARKET OUTLOOK
Write 3 sentences on current Indian market conditions and key risks.

RULES:
- SIGNAL must be exactly: BUY, HOLD, or SELL
- Every portfolio item must appear with a signal
- Watchlist: only show items worth buying right now
- Reason: plain English, max 15 words, no jargon
- Keep CODE/KEY exactly as given

==============================
MY PORTFOLIO - STOCKS
==============================
{block(stock_data)}

==============================
MY PORTFOLIO - MUTUAL FUNDS
==============================
{block(mf_data)}

==============================
WATCHLIST - STOCKS
==============================
{block(wl_stocks)}

==============================
WATCHLIST - MUTUAL FUNDS
==============================
{block(wl_mf)}

==============================
WATCHLIST - ETFs
==============================
{block(wl_etf)}
"""


def analyse_with_gemini(stock_data, mf_data, wl_stocks, wl_mf, wl_etf) -> str:
    prompt = build_prompt(stock_data, mf_data, wl_stocks, wl_mf, wl_etf)
    client = genai.Client(api_key=GEMINI_API_KEY)

    print(f"\n[4/5] Sending to Gemini for analysis using {GEMINI_MODEL} (please wait ~20s)...")
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        raw = response.text or ""
    finally:
        client.close()

    print("\n─── Gemini response ───")
    print(raw)
    print("───────────────────────")
    return raw


# ══════════════════════════════════════════════════════════════
#  PARSE GEMINI RESPONSE
# ══════════════════════════════════════════════════════════════

def extract_current_price(summary: str) -> str:
    for label in ("Current price:", "Current NAV:"):
        if label in summary:
            price_line = summary.split(label, 1)[1].splitlines()[0].strip()
            return price_line
    return ""


def parse_response(raw: str, stock_data: dict, mf_data: dict, wl_stocks: dict, wl_mf: dict, wl_etf: dict) -> dict:
    sections = {
        "port_stocks": [],
        "port_mf":     [],
        "wl_stocks":   [],
        "wl_mf":       [],
        "wl_etf":      [],
        "outlook":     "",
    }
    price_map = {}
    for data in (stock_data, mf_data, wl_stocks, wl_mf, wl_etf):
        for key, summary in data.items():
            price_map[key] = extract_current_price(summary)
    MARKERS = {
        "## portfolio stocks":        "port_stocks",
        "## portfolio mutual funds":  "port_mf",
        "## watchlist - stock picks": "wl_stocks",
        "## watchlist - mf picks":    "wl_mf",
        "## watchlist - etf picks":   "wl_etf",
        "## market outlook":          "outlook",
    }
    current = None
    for line in raw.splitlines():
        s   = line.strip()
        low = s.lower()

        matched = False
        for marker, key in MARKERS.items():
            if marker in low:
                current = key
                matched = True
                break
        if matched or not s:
            continue

        if current == "outlook":
            sections["outlook"] += s + " "
        elif current and "|" in s:
            parts = [p.strip() for p in s.split("|")]
            if len(parts) >= 3:
                name   = parts[0]
                signal = parts[1].upper().replace("*", "").strip()
                reason = " ".join(parts[2:]).replace("*", "").strip()
                if signal in ("BUY", "HOLD", "SELL"):
                    price = price_map.get(name, "")
                    sections[current].append((name, signal, price, reason))
    return sections


# ══════════════════════════════════════════════════════════════
#  HTML EMAIL BUILDER
# ══════════════════════════════════════════════════════════════

SIGNAL_CSS = {
    "BUY":  ("background:#e6f9ee;color:#1a7a3c;border-left:4px solid #1a7a3c;", "▲ BUY"),
    "SELL": ("background:#fff0f0;color:#c0392b;border-left:4px solid #c0392b;", "▼ SELL"),
    "HOLD": ("background:#fffbe6;color:#8a6d00;border-left:4px solid #f0c000;", "◆ HOLD"),
}

def make_table(rows, col1="Symbol"):
    if not rows:
        return "<p style='color:#999;font-size:13px;font-style:italic;'>No data returned</p>"
    thead = (
        f"<thead><tr style='background:#e8eaf6;color:#1a237e;"
        f"font-size:12px;text-transform:uppercase;'>"
        f"<th style='padding:9px 12px;text-align:left;'>{col1}</th>"
        f"<th style='padding:9px 12px;text-align:left;'>Current Price</th>"
        f"<th style='padding:9px 12px;text-align:left;'>Signal</th>"
        f"<th style='padding:9px 12px;text-align:left;'>Reason</th>"
        f"</tr></thead>"
    )
    tbody = ""
    for row in rows:
        if len(row) == 4:
            name, signal, price, reason = row
        else:
            name, signal, reason = row
            price = ""
        display_price = price or "—"
        css, label = SIGNAL_CSS.get(signal, ("", signal))
        tbody += (
            f"<tr>"
            f"<td style='padding:9px 12px;font-weight:600;font-size:14px;"
            f"border-bottom:1px solid #f0f0f0;'>{name}</td>"
            f"<td style='padding:9px 12px;border-bottom:1px solid #f0f0f0;color:#444;"
            f"font-size:13px;'>{display_price}</td>"
            f"<td style='padding:9px 12px;border-bottom:1px solid #f0f0f0;'>"
            f"<span style='padding:3px 10px;border-radius:4px;font-weight:700;"
            f"font-size:12px;{css}'>{label}</span></td>"
            f"<td style='padding:9px 12px;color:#444;font-size:13px;"
            f"border-bottom:1px solid #f0f0f0;'>{reason}</td>"
            f"</tr>"
        )
    return (
        f"<table style='width:100%;border-collapse:collapse;background:#fff;"
        f"border-radius:8px;overflow:hidden;"
        f"box-shadow:0 1px 4px rgba(0,0,0,.08);'>"
        f"{thead}<tbody>{tbody}</tbody></table>"
    )


def make_section(title, emoji, rows, col1="Symbol"):
    return (
        f"<h2 style='margin:28px 0 10px;font-size:17px;color:#1a237e;'>"
        f"{emoji} {title}</h2>"
        f"{make_table(rows, col1)}"
    )


def build_html(sections: dict) -> str:
    today_str = datetime.date.today().strftime("%d %B %Y")

    all_rows = sections["port_stocks"] + sections["port_mf"]
    buys  = sum(1 for _, s, *_ in all_rows if s == "BUY")
    holds = sum(1 for _, s, *_ in all_rows if s == "HOLD")
    sells = sum(1 for _, s, *_ in all_rows if s == "SELL")

    summary_bar = (
        "<div style='display:flex;gap:12px;margin:0 0 24px;'>"
        f"<div style='flex:1;padding:14px;background:#e6f9ee;border-radius:8px;text-align:center;'>"
        f"<div style='font-size:26px;font-weight:700;color:#1a7a3c;'>{buys}</div>"
        f"<div style='font-size:12px;color:#1a7a3c;margin-top:2px;'>BUY</div></div>"
        f"<div style='flex:1;padding:14px;background:#fffbe6;border-radius:8px;text-align:center;'>"
        f"<div style='font-size:26px;font-weight:700;color:#8a6d00;'>{holds}</div>"
        f"<div style='font-size:12px;color:#8a6d00;margin-top:2px;'>HOLD</div></div>"
        f"<div style='flex:1;padding:14px;background:#fff0f0;border-radius:8px;text-align:center;'>"
        f"<div style='font-size:26px;font-weight:700;color:#c0392b;'>{sells}</div>"
        f"<div style='font-size:12px;color:#c0392b;margin-top:2px;'>SELL</div></div>"
        "</div>"
    )

    wl_html = ""
    if sections["wl_stocks"] or sections["wl_mf"] or sections["wl_etf"]:
        wl_html = (
            "<hr style='border:none;border-top:1px solid #e8eaf6;margin:32px 0;'>"
            "<h2 style='margin:0 0 4px;font-size:18px;color:#1a237e;'>"
            "🔎 Market Picks — New Opportunities</h2>"
            "<p style='margin:0 0 16px;font-size:13px;color:#888;'>"
            "Gemini's top BUY picks from the broader NSE/BSE universe</p>"
        )
        if sections["wl_stocks"]:
            wl_html += make_section("Top Stock Picks", "📈", sections["wl_stocks"], "Stock")
        if sections["wl_mf"]:
            wl_html += make_section("Top Mutual Fund Picks", "🏦", sections["wl_mf"], "Fund")
        if sections["wl_etf"]:
            wl_html += make_section("Top ETF Picks", "⚡", sections["wl_etf"], "ETF")

    outlook_html = ""
    if sections["outlook"].strip():
        outlook_html = (
            "<div style='margin:28px 0 0;padding:16px 20px;background:#f0f4ff;"
            "border-radius:8px;border-left:4px solid #3949ab;'>"
            "<h3 style='margin:0 0 8px;font-size:15px;color:#1a237e;'>📈 Market Outlook</h3>"
            f"<p style='margin:0;font-size:14px;color:#333;line-height:1.7;'>"
            f"{sections['outlook'].strip()}</p></div>"
        )

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:Arial,Helvetica,sans-serif;">
<div style="max-width:660px;margin:20px auto;background:#fff;border-radius:12px;
     overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.12);">

  <!-- Header -->
  <div style="background:#1a237e;padding:26px 28px;">
    <h1 style="margin:0;color:#fff;font-size:22px;font-weight:700;">
      📊 Portfolio Report</h1>
    <p style="margin:6px 0 0;color:#9fa8da;font-size:13px;">
      {today_str} &nbsp;·&nbsp; Powered by Google Gemini AI</p>
  </div>

  <div style="padding:24px 28px;">
    {summary_bar}
    {make_section("My Stocks", "💼", sections["port_stocks"], "Code")}
    {make_section("My Mutual Funds", "🏦", sections["port_mf"], "Fund")}
    {wl_html}
    {outlook_html}
  </div>

  <!-- Footer -->
  <div style="padding:16px 28px;background:#f8f9ff;border-top:1px solid #e8eaf6;
       font-size:11px;color:#aaa;text-align:center;line-height:1.6;">
    ⚠️ This report is AI-generated for informational purposes only.<br>
    <strong>Not financial advice.</strong>
    Consult a SEBI-registered advisor before investing.
  </div>
</div>
</body>
</html>"""


# ══════════════════════════════════════════════════════════════
#  SEND EMAIL
# ══════════════════════════════════════════════════════════════

def send_email(html_body: str):
    today_str = datetime.date.today().strftime("%d %b %Y")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📊 Portfolio Report — {today_str}"
    msg["From"]    = GMAIL_USER
    msg["To"]      = NOTIFY_EMAIL
    msg.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            s.sendmail(GMAIL_USER, NOTIFY_EMAIL, msg.as_string())
        print(f"  ✅ Email sent → {NOTIFY_EMAIL}")
    except Exception as e:
        print(f"  ❌ Email failed: {e}")
        print("     Check GMAIL_USER and GMAIL_APP_PASSWORD are correct.")


# ══════════════════════════════════════════════════════════════
#  SEND TELEGRAM (optional)
# ══════════════════════════════════════════════════════════════

def send_telegram(sections: dict):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    today_str = datetime.date.today().strftime("%d %b %Y")
    emo = {"BUY": "🟢", "HOLD": "🟡", "SELL": "🔴"}

    def shorten_text(value: str, max_len: int = 120) -> str:
        text = value.replace("\n", " ").strip()
        if len(text) <= max_len:
            return text
        return text[: max_len - 1].rstrip() + "…"

    def append_section(title: str, rows, limit: int):
        lines = []
        if not rows:
            return lines
        lines.append(title)
        for row in rows[:limit]:
            if len(row) == 4:
                name, sig, price, reason = row
            else:
                name, sig, reason = row
                price = ""
            price_text = f" {price}" if price else ""
            lines.append(
                f"{emo.get(sig,'')} {shorten_text(name, 30)}{price_text} {sig} - {shorten_text(reason, 80)}"
            )
        if len(rows) > limit:
            lines.append(f"...and {len(rows) - limit} more")
        return lines

    lines = [f"Portfolio Report — {today_str}", ""]
    lines += append_section("Stocks:", sections["port_stocks"], 6)
    lines.append("")
    lines += append_section("Mutual Funds:", sections["port_mf"], 6)

    watchlist = sections["wl_stocks"] + sections["wl_mf"] + sections["wl_etf"]
    if watchlist:
        lines.append("")
        lines.append("Top BUY Picks:")
        for row in watchlist[:8]:
            if len(row) == 4:
                name, sig, price, reason = row
            else:
                name, sig, reason = row
                price = ""
            price_text = f" {price}" if price else ""
            lines.append(f"🟢 {shorten_text(name, 30)}{price_text} - {shorten_text(reason, 80)}")
        if len(watchlist) > 8:
            lines.append(f"...and {len(watchlist) - 8} more")

    if sections["outlook"]:
        lines.append("")
        lines.append(f"Market outlook: {shorten_text(sections['outlook'], 280)}")

    text = "\n".join(lines)
    if len(text) > 3900:
        text = text[:3890].rstrip() + "\n...message truncated..."

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            timeout=10
        )
        print("  ✅ Telegram sent" if r.ok else f"  ❌ Telegram: {r.text}")
    except Exception as e:
        print(f"  ❌ Telegram failed: {e}")


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    validate_config()
    print("=" * 55)
    print("  Portfolio Analyser — Google Gemini Edition")
    print(f"  {datetime.date.today().strftime('%d %B %Y')}")
    print("=" * 55)

    stock_data, mf_data, wl_stocks, wl_mf, wl_etf = fetch_all_data()
    raw      = analyse_with_gemini(stock_data, mf_data, wl_stocks, wl_mf, wl_etf)
    sections = parse_response(raw, stock_data, mf_data, wl_stocks, wl_mf, wl_etf)

    print("\n[5/5] Sending report...")
    html = build_html(sections)
    send_email(html)
    send_telegram(sections)

    print("\n✅ All done! Check your inbox.")


if __name__ == "__main__":
    main()