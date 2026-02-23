# HyperIndex - Self-Contained Dashboard

A real-time Hyperliquid smart money tracking dashboard.

## Quick Start

```bash
# Generate data (one-shot)
python generator.py

# Start local server
python -m http.server 3000

# View at http://localhost:3000
```

## Folder Structure

```
HyperIndex/
├── index.html          # Dashboard (main entry point)
├── generator.py        # Data generator script
├── config/
│   └── wallets.txt     # Cohort wallet addresses (one per line)
├── data/
│   ├── index_latest.json   # Current snapshot
│   ├── history.json        # Historical data (self-maintained)
│   ├── .health             # Health status
│   └── backups/            # Rolling backups
├── images/
│   ├── logo-icon.jpg
│   └── logo-wordmark.jpg
└── logs/
    └── generator.log
```

## Scheduling

### Free Tier (Twice Daily)
```bash
# Add to crontab (crontab -e)
0 8,20 * * * cd /path/to/HyperIndex && python3 generator.py
```

### Paid Tier (Every 5 Minutes)
```bash
*/5 * * * * cd /path/to/HyperIndex && python3 generator.py
```

## Updating the Cohort

1. Edit `config/wallets.txt` (one address per line)
2. Run `python generator.py` to regenerate
3. History will continue from the new cohort

## Deployment

This folder is fully self-contained. To deploy:

1. Copy entire `HyperIndex/` folder to server
2. Set up cron for `generator.py`
3. Serve files via nginx/Apache/etc.
4. Point domain to `index.html`

## Requirements

- Python 3.8+
- `requests` library (usually pre-installed)

No API keys or secrets needed - uses public Hyperliquid data.
