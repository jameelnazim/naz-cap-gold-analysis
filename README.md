# ◈ GIT — Gold Intelligence Terminal v4.0

A live institutional-grade gold trading terminal with real-time market data, news intelligence, technical analysis, historical analog matching, and AI-powered directional bias engine. Deploy on Render in under 10 minutes.

---

## WHAT'S INSIDE

- **Live Market Dashboard** — XAU/USD, DXY, US10Y, US2Y, TIPS, VIX, SPX, DOW, NASDAQ, WTI, Natural Gas, Silver, Copper, EUR/USD, GBP/USD, USD/JPY, USD/CNH, GLD ETF, GDX, SLV — all live with 30s auto-refresh
- **Macro Intelligence** — Hawkish Index 0–100, FedWatch rate probabilities, yield curve analysis, real yield transmission model
- **News Intelligence** — Pulls Reuters, Kitco, MarketWatch, Bloomberg, Investing.com — filters gold-relevant news, classifies each as Bullish/Bearish/Neutral with transmission channel
- **Historical Analogs** — Matches current conditions to past events (CPI shocks, NFP beats, Fed pivots, geopolitical crises) with 24h and 72h gold price projections
- **Technical Intelligence** — RSI, EMA 20/50/200, VWAP, ATR, Market Structure, Fair Value Gaps, Liquidity Zones, Trend Phase, PO3
- **Composite Bias Engine** — 0–100 score combining macro + technical, with confidence rating and NY session probability windows
- **Session Clock** — Live EST clock tracking Asian, London, NY killzones with countdown to NY open/close

---

## DEPLOY TO RENDER (Full Guide)

### STEP 1 — CREATE A GITHUB ACCOUNT (if you don't have one)

1. Go to **github.com**
2. Click **Sign up**
3. Enter email, create password, choose username
4. Verify your email

---

### STEP 2 — CREATE A NEW GITHUB REPOSITORY

1. Log into GitHub
2. Click the **+** button (top right) → **New repository**
3. Fill in:
   - **Repository name:** `git-gold-terminal`
   - **Description:** Gold Intelligence Terminal
   - Set to **Public** (required for free Render)
   - ✅ Check **Add a README file**
4. Click **Create repository**

---

### STEP 3 — UPLOAD THE PROJECT FILES

You need to upload these files to your GitHub repository:

```
git-gold-terminal/
├── app.py
├── requirements.txt
├── Procfile
├── render.yaml
├── runtime.txt
└── templates/
    └── index.html
```

**Method A: Upload via GitHub website (easiest)**

1. Open your new repository on GitHub
2. Click **Add file** → **Upload files**
3. Drag and drop: `app.py`, `requirements.txt`, `Procfile`, `render.yaml`, `runtime.txt`
4. Click **Commit changes**
5. Now create the templates folder:
   - Click **Add file** → **Create new file**
   - In the filename box type: `templates/index.html`
   - Paste the entire content of `index.html` into the editor
   - Click **Commit new file**

**Method B: Using Git (if you have Git installed)**

```bash
# In terminal/command prompt:
git clone https://github.com/YOUR_USERNAME/git-gold-terminal.git
cd git-gold-terminal

# Copy all GIT files into this folder, then:
git add .
git commit -m "Initial GIT deployment"
git push origin main
```

---

### STEP 4 — CREATE A RENDER ACCOUNT

1. Go to **render.com**
2. Click **Get Started for Free**
3. Sign up with your **GitHub account** (click "Sign up with GitHub") — this connects them automatically
4. Authorize Render to access your GitHub

---

### STEP 5 — DEPLOY ON RENDER

1. On Render dashboard, click **New +** → **Web Service**
2. Click **Connect a repository**
3. Find and select **git-gold-terminal**
4. Click **Connect**
5. Fill in the settings:
   - **Name:** `git-gold-terminal`
   - **Region:** Oregon (US West) or Frankfurt (Europe)
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --workers 2 --timeout 120 --bind 0.0.0.0:$PORT`
6. Select **Free** plan
7. Click **Create Web Service**

Render will now:
- Pull your code from GitHub
- Install all Python packages
- Start the server
- Give you a live URL like: `https://git-gold-terminal.onrender.com`

**Build takes 3–5 minutes the first time.**

---

### STEP 6 — OPEN YOUR TERMINAL

Once deployment shows **"Live"** (green):

1. Click the URL shown on Render (e.g. `https://git-gold-terminal.onrender.com`)
2. The terminal will load and begin fetching live data
3. **First data load takes 20–30 seconds** while the backend pulls all market data
4. Bookmark the URL — this is your terminal forever

---

## IMPORTANT NOTES

### Free Tier Spin-Down
Render free tier **sleeps after 15 minutes of inactivity**. When you first open it after a break, it takes **30–60 seconds to wake up** and show the loader. After that it's fully live.

**To keep it always awake (optional):**
- Upgrade to Render Starter ($7/month), OR
- Use a free uptime service like UptimeRobot to ping your URL every 10 minutes

### Auto-Deploy
Every time you push code changes to GitHub, Render automatically re-deploys. No manual work needed.

---

## AUTO-UPDATES AFTER DEPLOYMENT

To update the terminal later:

1. Edit your files locally
2. Push to GitHub:
```bash
git add .
git commit -m "Update terminal"
git push
```
3. Render detects the change and automatically re-deploys in ~2 minutes

---

## FILE STRUCTURE

```
git-gold-terminal/
├── app.py              ← Flask backend (all data engines)
├── requirements.txt    ← Python dependencies
├── Procfile           ← Gunicorn start command for Render
├── render.yaml        ← Render configuration
├── runtime.txt        ← Python version specification
└── templates/
    └── index.html     ← Full terminal UI (served by Flask)
```

---

## DATA SOURCES

| Data | Source | Refresh |
|------|--------|---------|
| Market prices | Yahoo Finance (yfinance) | 30 seconds |
| Gold technicals | Yahoo Finance OHLCV | 30 seconds |
| News feed | Reuters, Kitco, MarketWatch, Investing.com | 30 seconds |
| FedWatch model | Derived from yield curve | 30 seconds |
| Historical analogs | Embedded database | Static |

---

## TROUBLESHOOTING

**"Data loading, please wait" stays for more than 60 seconds**
→ Render free tier is waking up. Wait 60 seconds and refresh.

**Market prices show "—"**
→ Yahoo Finance may be temporarily rate-limiting. Wait 30s, refresh again.

**Build fails on Render**
→ Check that all 5 files are in the repository with exact filenames.
→ Check Render logs: Dashboard → Your service → Logs tab

**News section shows no articles**
→ RSS feeds may be slow. Market data still works. News refreshes every 30s.

**Port error**
→ Render sets `$PORT` automatically. The Procfile handles this correctly.

---

## DISCLAIMER

GIT is for informational and educational purposes only.
This is not financial advice. Trading involves risk of loss.
Data sourced from Yahoo Finance and public RSS feeds.
Always verify data independently before making trading decisions.
