# HyperIndex

**Real-time smart money positioning dashboard for Hyperliquid.**

HyperIndex tracks a curated cohort of elite wallets on Hyperliquid and aggregates their positioning into a single dashboard — showing net exposure, conviction scores, tilt, and leverage across all tracked assets.

---

## What It Does

- Tracks a cohort of high-performing Hyperliquid wallets
- Aggregates long/short positioning across all perp assets
- Calculates conviction, tilt (T_s), and net leverage metrics
- Serves a live web dashboard with historical charting
- Updates on a scheduled cadence via a lightweight Python generator

No API keys required — all data is sourced from the public Hyperliquid API.

---

## Stack

- **Frontend:** Static HTML + vanilla JS + Chart.js + Tailwind CSS
- **Data layer:** Python (`generator.py`) — queries Hyperliquid, writes JSON
- **Scheduling:** `scheduler.py` — runs the generator on a set cadence
- **Monitoring:** `monitor.py` — terminal dashboard for operational visibility

---

## Project Structure

```
HyperIndex/
├── index.html              # Dashboard (main entry point)
├── generator.py            # Data generator
├── scheduler.py            # Scheduling daemon
├── monitor.py              # Terminal monitor
├── config/
│   └── wallets.txt         # Cohort wallet addresses (one per line)
├── data/                   # Generated data (gitignored)
│   ├── index_latest.json
│   ├── history.json
│   └── backups/
├── images/
│   ├── logo-icon.jpg
│   └── logo-wordmark.jpg
└── logs/                   # Runtime logs (gitignored)
```

---

## Running Locally

**Requirements:** Python 3.8+, `requests` library

```bash
# Install dependencies
pip install requests

# Generate data (fetches live from Hyperliquid)
python3 generator.py

# Serve the dashboard
python3 -m http.server 3000
# → Open http://localhost:3000
```

---

## Scheduling

To keep data fresh, run the generator on a schedule:

```bash
# Example: 4x daily via cron
0 0,6,12,18 * * * cd /path/to/HyperIndex && python3 generator.py

# Or use the built-in scheduler daemon
python3 scheduler.py
```

---

## Updating the Cohort

1. Edit `config/wallets.txt` (one address per line)
2. Update `COHORT_REBALANCED_AT` in `generator.py`
3. Run `python3 generator.py` to regenerate with the new cohort

---

## Deployment

The project is fully self-contained. To deploy:

1. Copy the `HyperIndex/` folder to your server
2. Set up a cron job or run `scheduler.py` as a daemon
3. Serve static files via nginx, Caddy, or any static host
4. Point your domain to `index.html`

---

## Disclaimer

Not financial advice. Data is aggregated from public on-chain activity and is provided for informational purposes only. Use at your own risk.
