# Portfolio Analyser — Full Project Reference

> This document captures all design decisions, code, configuration, and setup
> instructions from the project discussion. Use it as context for any future
> Claude.ai chat to continue or modify this project.

---

## Project Goal

Build an automated **Indian stock & mutual fund portfolio analyser** that:
- Fetches live market data (NSE stocks + MF NAVs)
- Uses an **LLM (Google Gemini)** to analyse and produce BUY / HOLD / SELL signals with one-line reasons
- Delivers a **rich HTML report to Gmail** (readable on phone)
- Optionally sends a **Telegram alert**
- Runs daily on a schedule (Windows Task Scheduler or cron)

---

## Architecture Overview

```
Data Sources
  ├── NSE/BSE stocks     → yfinance (Python library, free)
  ├── Mutual Fund NAVs   → mfapi.in (free REST API, no key needed)
  └── Watchlist stocks   → yfinance

         ↓

Analysis Engine (Python)
  ├── Compute RSI, SMA20, SMA50, 30d/90d price change
  └── Send all data to Google Gemini Flash (free API)
      → Returns: TICKER | BUY/HOLD/SELL | Reason

         ↓

Report Builder
  └── Build HTML email with signal summary, tables, market outlook

         ↓

Delivery
  ├── Gmail (SMTP via smtplib — built into Python)
  └── Telegram bot (optional, free)
```

---

## Technology Stack

| Component | Tool | Cost |
|---|---|---|
| Stock data | `yfinance` Python library | Free |
| MF NAV data | `mfapi.in` REST API | Free |
| LLM analysis | Google Gemini 1.5 Flash | Free (1500 req/day) |
| Email delivery | Gmail SMTP (`smtplib`) | Free |
| Telegram alert | Telegram Bot API | Free |
| Scheduler | Windows Task Scheduler / cron | Free |

---

## Python Libraries Required

```powershell
pip install yfinance requests google-generativeai
```

- `yfinance` — NSE/BSE stock prices, historical data, PE, 52w high/low
- `requests` — MF NAV from mfapi.in + Telegram API calls
- `google-generativeai` — Google Gemini API client
- `smtplib`, `datetime`, `os`, `time` — built into Python, no install needed

---

## API Keys & Credentials

### Google Gemini API Key (FREE)
1. Go to: https://aistudio.google.com/app/apikey
2. Sign in with Google account
3. Click **Create API Key**
4. Copy key — starts with `AIzaSy...`
5. Free limits: 15 requests/minute, 1500 requests/day

### Gmail App Password
1. Go to: https://myaccount.google.com/security
2. Enable **2-Step Verification** (required)
3. Search for **App Passwords**
4. Generate for Mail / Windows Computer
5. Copy the 16-character password (e.g. `abcd efgh ijkl mnop`)
- This is NOT your Gmail login password
- Used only for SMTP sending from the script

### Telegram Bot (Optional)
1. Open Telegram → search `@BotFather`
2. Send `/newbot` → follow prompts → copy token (`bot123456:ABC-...`)
3. Get your chat ID from `@userinfobot`

---

## Environment Variables Setup (Windows PowerShell)

### Set for current session only
```powershell
$env:GEMINI_API_KEY     = "AIzaSy-your-key-here"
$env:GMAIL_USER         = "you@gmail.com"
$env:GMAIL_APP_PASSWORD = "abcdabcdabcdabcd"
$env:NOTIFY_EMAIL       = "you@gmail.com"
```

### Set permanently (run once as Administrator)
```powershell
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY",     "AIzaSy-your-key-here",  "User")
[System.Environment]::SetEnvironmentVariable("GMAIL_USER",         "you@gmail.com",          "User")
[System.Environment]::SetEnvironmentVariable("GMAIL_APP_PASSWORD", "abcdabcdabcdabcd",       "User")
[System.Environment]::SetEnvironmentVariable("NOTIFY_EMAIL",       "you@gmail.com",           "User")
```
Restart PowerShell after running the above.

---

## Your Portfolio

### Stocks (16 holdings)

| Your Code | NSE Ticker | Company Name |
|---|---|---|
| EXIIND | EXIDEIND.NS | Exide Industries |
| HDFBAN | HDFCBANK.NS | HDFC Bank |
| ICIBAN | ICICIBANK.NS | ICICI Bank |
| STABAN | SBIN.NS | State Bank of India |
| YESBAN | YESBANK.NS | Yes Bank |
| GOLDEX | GOLDBEES.NS | Nippon Gold ETF |
| NIPSIL | SILVERBEES.NS | Nippon Silver ETF |
| SRSLIM | SHRIRAMFIN.NS | Shriram Finance |
| HCLTEC | HCLTECH.NS | HCL Technologies |
| INFTEC | INFY.NS | Infosys |
| TCS | TCS.NS | Tata Consultancy Services |
| RELINF | RELIANCE.NS | Reliance Industries |
| LIC | LICI.NS | LIC of India |
| ADAGRE | ADANIGREEN.NS | Adani Green Energy |
| ADAPOW | ADANIPOWER.NS | Adani Power |
| INDOIL | IOC.NS | Indian Oil Corporation |

### Mutual Funds (12 schemes)

| Key in Script | Scheme Code | Fund Name |
|---|---|---|
| ICICI_LARGECAP | 120586 | ICICI Pru Large Cap Fund - Growth |
| HDFC_MIDCAP_G | 119062 | HDFC Mid Cap Fund - Growth |
| HDFC_MIDCAP_IDCW | 119065 | HDFC Mid Cap Fund - IDCW |
| HSBC_MIDCAP | 145552 | HSBC Midcap Fund - IDCW |
| AXIS_MULTICAP | 120841 | Axis Multicap Fund - Regular Growth |
| ICICI_INFRA | 120505 | ICICI Pru Infrastructure Fund - Growth |
| FRANKLIN_SMALL | 118989 | Franklin India Small Cap Fund - Growth |
| HSBC_VALUE | 145547 | HSBC Value Fund - Growth |
| ICICI_VALUE | 120578 | ICICI Pru Value Discovery Fund - Growth |
| NIPPON_GOLD_FOF | 118701 | Nippon India Gold Savings Fund - Growth |
| NIPPON_SILVER_FOF | 149645 | Nippon India Silver ETF FOF - Growth |
| NAVI_NIFTY50 | 145920 | Navi Nifty 50 Index Fund - Regular Growth |

> **Note on MF scheme codes:** mfapi.in occasionally renumbers schemes after
> fund mergers. If a fund shows "Error", search the current code at:
> `https://api.mfapi.in/mf/search?q=FUND+NAME`

### Watchlist (screened by Gemini for new BUY picks)

**Stocks:** Bajaj Finance, Maruti Suzuki, Sun Pharma, Titan, Kotak Bank,
Hindustan Unilever, L&T, UltraTech Cement, Asian Paints, Wipro, Tata Motors,
Bajaj Finserv, NTPC, Power Grid, Nestle India

**MFs:** Axis Bluechip, Parag Parikh Flexi Cap, SBI Small Cap,
Kotak Emerging Equity, Quant Small Cap

**ETFs:** Nippon Nifty BeES, Nippon Junior BeES, Nippon Bank BeES,
Motilal Oswal Momentum 100, SBI Nifty 50 ETF

---

## Data Collected Per Stock

For each NSE stock, the script fetches and sends to Gemini:
- Current price, 30-day change %, 90-day change %
- 52-week high and low
- PE ratio, Market cap, Sector
- RSI (14-day), SMA 20, SMA 50
- Average volume (20-day)
- Last 10 closing prices

For each Mutual Fund:
- Current NAV, 30-day change %, 90-day change %
- 90-day high/low NAV
- RSI (14-day) computed on NAV series
- Last 10 NAV values

---

## Gemini Prompt Design

Gemini is asked to produce output in strict pipe-separated format:

```
## PORTFOLIO STOCKS
CODE | SIGNAL | Reason (max 15 words)

## PORTFOLIO MUTUAL FUNDS
KEY | SIGNAL | Reason (max 15 words)

## WATCHLIST - STOCK PICKS (BUY only)
NAME | BUY | Reason (max 15 words)

## WATCHLIST - MF PICKS (BUY only)
NAME | BUY | Reason (max 15 words)

## WATCHLIST - ETF PICKS (BUY only)
NAME | BUY | Reason (max 15 words)

## MARKET OUTLOOK
3 sentences on current Indian market conditions.
```

Rules enforced in the prompt:
- SIGNAL must be exactly BUY, HOLD, or SELL
- Every portfolio item must appear
- Watchlist: only genuine BUY recommendations
- Reason: plain English, max 15 words, no jargon

Model used: `gemini-1.5-flash` (free tier)

---

## Email Report Structure

The HTML email sent to Gmail contains:

1. **Header** — dark blue banner with date and "Powered by Google Gemini AI"
2. **Signal summary bar** — large BUY / HOLD / SELL counts at a glance
3. **My Stocks table** — all 16 stocks with colour-coded signal + reason
4. **My Mutual Funds table** — all 12 MFs with signal + reason
5. **Market Picks section** — new BUY opportunities from watchlist (stocks, MFs, ETFs)
6. **Market Outlook** — 3-sentence AI summary of current Indian market
7. **Footer** — disclaimer: not financial advice

Signal colour coding:
- BUY → green background `#e6f9ee` with green text
- HOLD → yellow background `#fffbe6` with amber text
- SELL → red background `#fff0f0` with red text

---

## Running the Script

```powershell
cd C:\PortfolioBot
python portfolio_analyser.py
```

Expected terminal output:
```
=======================================================
  Portfolio Analyser — Google Gemini Edition
  01 June 2025
=======================================================

[1/5] Fetching your stock portfolio...
  ✓ EXIIND (EXIDEIND.NS)
  ✓ HDFBAN (HDFCBANK.NS)
  ... all 16 stocks

[2/5] Fetching your mutual fund NAVs...
  ✓ ICICI_LARGECAP
  ... all 12 funds

[3/5] Fetching watchlist data...
  ... stocks + MFs + ETFs

[4/5] Sending to Gemini for analysis (please wait ~20s)...

─── Gemini response ───
## PORTFOLIO STOCKS
EXIIND | HOLD | Near fair value, no strong momentum signal
...
───────────────────────

[5/5] Sending report...
  ✅ Email sent → you@gmail.com

✅ All done! Check your inbox.
```

---

## Scheduling Daily Runs (Windows)

Run once in PowerShell to create a daily Task Scheduler job at 8 AM:

```powershell
$action  = New-ScheduledTaskAction -Execute "python" -Argument "C:\PortfolioBot\portfolio_analyser.py"
$trigger = New-ScheduledTaskTrigger -Daily -At 8:00AM
Register-ScheduledTask -TaskName "PortfolioReport" -Action $action -Trigger $trigger -RunLevel Highest
```

Replace `C:\PortfolioBot\` with your actual folder path.

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: google.generativeai` | Library not installed | `pip install google-generativeai` |
| `API key not valid` | Wrong Gemini key | Check `$env:GEMINI_API_KEY` |
| `SMTPAuthenticationError` | Wrong Gmail App Password | Regenerate at myaccount.google.com |
| `No data available` for a stock | NSE ticker changed | Search correct ticker on finance.yahoo.com |
| MF shows `Error` | Scheme code changed | Search at `https://api.mfapi.in/mf/search?q=FUND+NAME` |
| `No module named yfinance` | Library not installed | `pip install yfinance` |

---

## Alternative LLM Options Considered

| Option | Cost | Quality | Notes |
|---|---|---|---|
| **Google Gemini Flash** ✅ | Free | Very good | Chosen option. 1500 req/day free |
| Groq (Llama 3.3 70B) | Free tier | Very good | `pip install groq`, fast |
| Ollama (local) | Free forever | Good | Runs on your PC, needs 4GB RAM, no internet |
| Anthropic Claude | $0.03–0.05/run | Excellent | Paid, ~$1.50/month for daily runs |

---

## Key Files

| File | Purpose |
|---|---|
| `portfolio_analyser.py` | Main Python script — complete, ready to run |
| `portfolio_analyser_reference.md` | This file — full project reference |

---

## Possible Future Enhancements

- Add **quantity and buy price** per holding to calculate P&L and % gain/loss
- Add **portfolio allocation pie chart** as an image in the email
- Add **price alerts** — notify if any stock drops more than X% in a day
- Switch watchlist to **Nifty 500 full universe** for broader screening
- Add **weekly deep-dive mode** vs daily quick mode
- Store historical signals in a CSV to track accuracy over time
- Add **WhatsApp delivery** via Twilio or WATI API

---

*Generated on: 31 May 2026*
*Project: Indian Portfolio Analyser — Gemini + Gmail Edition*
