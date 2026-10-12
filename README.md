# Daily Market Dashboard

A static market dashboard that auto-refreshes daily at **1:00 PM PT** on weekdays via GitHub Actions. Data sourced from Yahoo Finance.

---

## What This Dashboard Shows

- **Market Trend Regime** — 6-check system (SPY/QQQ vs EMAs, breadth, offense vs defense, VIX)
- **Market Commentary** — Auto-generated daily summary
- **Primary Themes** — Sector rotation, focus themes, top gainers
- **Market Breadth** — New highs/lows (you paste 2 numbers from TradingView)
- **Situational Awareness** — Economic calendar
- **Major Indexes** — SPY, QQQ, DIA, IWM with daily/5D/YTD/% off high
- **S&P 500 Sectors** — All 11 sectors ranked by 5-day performance
- **Thematic ETFs** — Semis, software, cybersecurity, solar, etc.
- **Macro** — VIX, gold, Treasuries, yields

---

## Setup (Step by Step)

### Step 1: Fork this repo on GitHub
1. Go to your GitHub account
2. Click the **"Fork"** button (top right)
3. Give it a name like `market-dashboard`

### Step 2: Enable GitHub Actions
1. In your forked repo, click **"Actions"** tab
2. Click the green button: **"I understand my workflows, go ahead and enable them"**

### Step 3: Run the workflow manually (first time)
1. In the **Actions** tab, click **"Refresh dashboard data"**
2. Click **"Run workflow"** → **"Run workflow"**
3. Wait ~2 minutes for it to finish
4. It will commit `data/snapshot.json` to your repo

### Step 4: Enable GitHub Pages
1. Go to **Settings** → **Pages** (left sidebar)
2. Under **Build and deployment**:
   - Source: **Deploy from a branch**
   - Branch: `main` / `root`
3. Click **Save**
4. Wait 1–2 minutes, then visit: `https://YOUR_USERNAME.github.io/market-dashboard/`

### Step 5: (Optional) Update the economic calendar
The economic calendar in the dashboard is hardcoded. To update it:
1. Go to your repo on GitHub
2. Click `index.html`
3. Click the **pencil icon** (edit)
4. Find the section with dates like `"Mon Oct 12"` and update them
5. Scroll down, click **"Commit changes"**

---

## Daily Workflow (After Setup)

Every weekday at **1:00 PM PT**, GitHub Actions will:
1. Fetch fresh market data from Yahoo Finance
2. Compute EMAs, SMAs, trend regime, commentary
3. Save `data/snapshot.json`
4. Your dashboard at the GitHub Pages URL updates automatically

**To add new highs/lows from TradingView:**
1. Open your dashboard
2. In Section 3 (Market Breadth), paste your TradingView numbers into the input boxes
3. The net NH-NL and trend automatically recalculate

---

## Files

| File | Purpose |
|------|---------|
| `scripts/build_data.py` | Fetches data, computes metrics, outputs JSON |
| `index.html` | Dashboard frontend (reads JSON, renders tables) |
| `.github/workflows/refresh_data.yml` | Cron job that runs daily |
| `data/snapshot.json` | Generated data (auto-committed by Actions) |

---

## Troubleshooting

**Dashboard shows "Loading market data..." forever?**
→ The workflow hasn't run yet. Go to Actions → Run workflow manually.

**Data looks old?**
→ Check the Actions tab. If the latest run failed, click it to see the error.

**Want to change the cron time?**
→ Edit `.github/workflows/refresh_data.yml` and change the cron line. Use [crontab.guru](https://crontab.guru) to generate times.

---

*Based on traderwillhu/market_dashboard. Modified for daily market recap format.*
