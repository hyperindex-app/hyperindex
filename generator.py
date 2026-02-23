"""
HyperIndex Data Generator (Self-Contained)

Generates JSON data for the HyperIndex dashboard.
Maintains its own history independent of any trading bot.

Usage:
    python generator.py              # One-shot generation
    python generator.py --schedule   # Run on schedule (default: 12h)
    python generator.py --interval 0.083  # Every 5 minutes (for paid tier)

Output:
    data/index_latest.json  - Current snapshot
    data/history.json       - Historical time-series (self-maintained)
    data/.health            - Health status for monitoring
"""

import sys
import json
import math
import time
import shutil
import argparse
import logging
import subprocess
import requests
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================================================================
# CONFIGURATION - All paths relative to this script
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Files
WALLETS_FILE = CONFIG_DIR / "wallets.txt"
INDEX_PATH = DATA_DIR / "index_latest.json"
HISTORY_PATH = DATA_DIR / "history.json"
HEALTH_FILE = DATA_DIR / ".health"
BACKUP_DIR = DATA_DIR / "backups"
LOG_FILE = LOGS_DIR / "generator.log"

# API
INFO_URL = "https://api.hyperliquid.xyz/info"

# Settings
MAX_BACKUPS = 5
MAX_HISTORY_POINTS = 2000  # Keep ~2 weeks at 15-min intervals
RETRY_ATTEMPTS = 3
RETRY_BACKOFF = 1.0

# Cohort rebalance date - update this when wallets.txt is updated
COHORT_REBALANCED_AT = "2026-02-18"

# ============================================================================
# LOGGING SETUP
# ============================================================================

LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# API SESSION WITH RETRY
# ============================================================================

def create_session():
    """Create requests session with automatic retries."""
    session = requests.Session()
    retries = Retry(
        total=RETRY_ATTEMPTS,
        backoff_factor=RETRY_BACKOFF,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"]
    )
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

api_session = create_session()

# ============================================================================
# WALLET LOADING
# ============================================================================

def load_wallets():
    """Load wallet addresses from config file."""
    if not WALLETS_FILE.exists():
        raise FileNotFoundError(f"Wallet file not found: {WALLETS_FILE}")

    wallets = []
    with WALLETS_FILE.open("r") as f:
        for line in f:
            w = line.strip()
            if w and w.startswith("0x") and len(w) == 42:
                wallets.append(w)

    if not wallets:
        raise ValueError(f"No valid wallets in {WALLETS_FILE}")

    # Check for duplicates
    if len(wallets) != len(set(wallets)):
        logger.warning("Duplicate wallet addresses detected in config!")
        wallets = list(dict.fromkeys(wallets))  # Remove duplicates, preserve order

    return wallets

# ============================================================================
# API CALLS
# ============================================================================

def get_positions(addr):
    """Fetch perp positions + equity for a wallet."""
    payload = {"type": "clearinghouseState", "user": addr}
    r = api_session.post(INFO_URL, json=payload, timeout=15)
    r.raise_for_status()
    data = r.json()

    margin_summary = data.get("marginSummary", {}) or data.get("margin_summary", {})
    account_value = margin_summary.get("accountValue") or margin_summary.get("account_value") or 0.0

    try:
        equity = float(account_value)
    except (TypeError, ValueError):
        equity = 0.0

    positions_raw = data.get("assetPositions", []) or data.get("asset_positions", [])
    positions = []

    for item in positions_raw:
        pos = item.get("position", {})
        if not pos:
            continue

        coin = pos.get("coin")
        size_str = pos.get("szi")
        position_value = pos.get("positionValue")
        leverage_obj = pos.get("leverage", {})
        leverage_value = leverage_obj.get("value") if isinstance(leverage_obj, dict) else None
        margin_used_str = pos.get("marginUsed")

        if not coin or not size_str:
            continue

        try:
            size = float(size_str)
            notional = float(position_value) if position_value else 0.0
            leverage = float(leverage_value) if leverage_value else 1.0

            if abs(size) < 1e-8 or notional < 1e-8:
                continue

            if margin_used_str is not None:
                margin_used = float(margin_used_str)
            else:
                margin_used = notional / leverage if leverage != 0 else notional
        except (TypeError, ValueError, ZeroDivisionError):
            continue

        positions.append({
            "coin": coin.upper(),
            "size": size,
            "notional": notional,
            "leverage": leverage,
            "margin_used": margin_used,
        })

    return positions, equity

# ============================================================================
# INDEX BUILDING
# ============================================================================

def build_index(wallets):
    """Build index data from wallet positions."""
    longs = defaultdict(float)
    shorts = defaultdict(float)
    margin_sum = defaultdict(float)
    position_count = defaultdict(int)
    total_equity = 0.0

    wallet_net = defaultdict(lambda: defaultdict(float))
    wallet_margin = defaultdict(lambda: defaultdict(float))
    wallet_equity = {}
    wallet_long_total = defaultdict(float)
    wallet_short_total = defaultdict(float)
    wallet_total_notional = defaultdict(float)

    failed = 0
    failed_wallets = []

    for i, addr in enumerate(wallets, 1):
        try:
            positions, equity = get_positions(addr)
        except Exception as e:
            logger.warning(f"[{i}/{len(wallets)}] Wallet {addr[:10]}... failed: {e}")
            failed += 1
            failed_wallets.append(addr[:10])
            continue

        total_equity += equity
        wallet_equity[addr] = equity

        for pos in positions:
            coin = pos["coin"]
            size = pos["size"]
            notional = pos["notional"]
            margin_used = pos["margin_used"]

            position_count[coin] += 1
            margin_sum[coin] += margin_used
            wallet_margin[addr][coin] += margin_used

            if size > 0:
                wallet_net[addr][coin] += notional
                longs[coin] += notional
                wallet_long_total[addr] += notional
            elif size < 0:
                wallet_net[addr][coin] -= notional
                shorts[coin] += notional
                wallet_short_total[addr] += notional
            wallet_total_notional[addr] += abs(notional)

        if i % 10 == 0:
            logger.info(f"[{i}/{len(wallets)}] wallets processed...")

    logger.info(f"Completed: {len(wallets) - failed}/{len(wallets)} wallets, equity=${total_equity:,.0f}")
    if failed > 0:
        logger.warning(f"Failed wallets ({failed}): {', '.join(failed_wallets)}")

    # Build asset rows
    MIN_NOTIONAL = 250_000

    coins = sorted(
        set(list(longs.keys()) + list(shorts.keys())),
        key=lambda c: longs[c] + shorts[c],
        reverse=True,
    )

    assets = []
    global_long = 0.0
    global_short = 0.0

    for coin in coins:
        long_n = longs[coin]
        short_n = shorts[coin]
        total = long_n + short_n
        if total <= 0:
            continue

        global_long += long_n
        global_short += short_n

        if long_n < MIN_NOTIONAL and short_n < MIN_NOTIONAL:
            continue

        net = long_n - short_n
        T_s = net / total if total > 0 else 0.0

        # L_net_margin
        msum = margin_sum[coin]
        L_net_margin = net / msum if msum > 0 else 0.0

        # L_net_equity
        L_net_equity = net / total_equity if total_equity > 0 else 0.0

        # Conviction (equity-based, sqrt-weighted)
        L_index_equity = 0.0
        weight_sum_equity = 0.0
        long_count = 0
        short_count = 0

        for addr in wallets:
            net_i = wallet_net[addr].get(coin, 0.0)
            if abs(net_i) < 1e-8:
                continue

            eq_i = wallet_equity.get(addr, 0.0)
            if eq_i <= 0:
                continue

            if net_i > 0:
                long_count += 1
            else:
                short_count += 1

            L_equity_i = net_i / eq_i
            if abs(L_equity_i) <= 0:
                continue

            sqrt_weight = math.sqrt(eq_i / 100_000.0) if eq_i > 0 else 0.0
            abs_L = abs(L_equity_i)
            sign = 1 if L_equity_i >= 0 else -1
            conv_e = abs_L * sqrt_weight
            L_index_equity += sign * abs_L * sqrt_weight
            weight_sum_equity += conv_e

        conv_equity = L_index_equity / weight_sum_equity if weight_sum_equity > 0 else 0.0

        asset_data = {
            "asset": coin,
            "long_usd": round(long_n, 2),
            "short_usd": round(short_n, 2),
            "net_usd": round(net, 2),
            "tilt": round(T_s, 4),
            "position_count": position_count[coin],
            "long_count": long_count,
            "short_count": short_count,
            "L_net_margin": round(L_net_margin, 6),
            "L_net_equity": round(L_net_equity, 6),
            "conv_equity": round(conv_equity, 4),
        }
        assets.append(asset_data)

    # Sort by absolute net position
    assets.sort(key=lambda a: abs(a["net_usd"]), reverse=True)

    # Mark top 5 as free (for freemium model)
    for i, asset in enumerate(assets):
        asset["free"] = i < 5

    # Cohort stats
    global_net = global_long - global_short
    gross_notional = global_long + global_short
    L_cohort_total = gross_notional / total_equity if total_equity > 0 else 0.0

    # Calculate overall index score
    total_abs_notional = sum(a["long_usd"] + a["short_usd"] for a in assets)
    if total_abs_notional > 0:
        index_score = sum(
            a["L_net_equity"] * (a["long_usd"] + a["short_usd"]) / total_abs_notional
            for a in assets
        )
    else:
        index_score = 0.0

    # Per-asset breakdown for history
    btc_data = next((a for a in assets if a["asset"] == "BTC"), None)
    eth_data = next((a for a in assets if a["asset"] == "ETH"), None)
    sol_data = next((a for a in assets if a["asset"] == "SOL"), None)
    hype_data = next((a for a in assets if a["asset"] == "HYPE"), None)

    output = {
        "generated_at": datetime.now().isoformat(),
        "cohort_rebalanced_at": COHORT_REBALANCED_AT,
        "index_score": round(index_score, 6),
        "leverage_dampening": False,
        "cohort_stats": {
            "total_equity": round(total_equity, 2),
            "total_wallets": len(wallets),
            "active_wallets": len([a for a in wallets if a in wallet_equity]),
            "gross_long_usd": round(global_long, 2),
            "gross_short_usd": round(global_short, 2),
            "net_usd": round(global_net, 2),
            "gross_notional_usd": round(gross_notional, 2),
            "L_cohort_total": round(L_cohort_total, 4),
        },
        "assets": assets,
        # Include key metrics for history tracking
        "_history_data": {
            "btc_net_usd": btc_data["net_usd"] if btc_data else 0,
            "eth_net_usd": eth_data["net_usd"] if eth_data else 0,
            "sol_net_usd": sol_data["net_usd"] if sol_data else 0,
            "hype_net_usd": hype_data["net_usd"] if hype_data else 0,
        }
    }

    return output

# ============================================================================
# HISTORY MANAGEMENT
# ============================================================================

def update_history(index_data):
    """Append current snapshot to history and maintain rolling window."""

    # Load existing history or create new
    if HISTORY_PATH.exists():
        try:
            with open(HISTORY_PATH, 'r') as f:
                history = json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning("Could not read history.json, starting fresh")
            history = {"hourly": [], "recent_24h": []}
    else:
        history = {"hourly": [], "recent_24h": []}

    # Create history point from current data
    stats = index_data["cohort_stats"]
    hist_data = index_data.get("_history_data", {})

    point = {
        "timestamp": index_data["generated_at"],
        "cohort_net_usd": stats["net_usd"],
        "gross_long_usd": stats["gross_long_usd"],
        "gross_short_usd": stats["gross_short_usd"],
        "L_cohort_total": stats["L_cohort_total"],
        "cohort_total_equity": stats["total_equity"],
        "cohort_num_wallets": stats["active_wallets"],
        "btc_net_usd": hist_data.get("btc_net_usd", 0),
        "eth_net_usd": hist_data.get("eth_net_usd", 0),
        "sol_net_usd": hist_data.get("sol_net_usd", 0),
        "hype_net_usd": hist_data.get("hype_net_usd", 0),
        "index_score": index_data["index_score"],
    }

    # Add to recent (full resolution)
    history.setdefault("recent_24h", []).append(point)

    # Trim recent to last 24 hours (96 points at 15-min intervals)
    if len(history["recent_24h"]) > 96:
        history["recent_24h"] = history["recent_24h"][-96:]

    # Add to hourly (downsample by keeping latest per hour)
    try:
        dt = datetime.fromisoformat(point["timestamp"])
        hour_key = dt.strftime("%Y-%m-%d %H:00")

        # Find if we already have this hour
        hourly = history.setdefault("hourly", [])
        existing_idx = None
        for i, h in enumerate(hourly):
            try:
                h_dt = datetime.fromisoformat(h["timestamp"])
                if h_dt.strftime("%Y-%m-%d %H:00") == hour_key:
                    existing_idx = i
                    break
            except:
                continue

        if existing_idx is not None:
            hourly[existing_idx] = point  # Update existing hour
        else:
            hourly.append(point)  # New hour

        # Trim hourly to max points
        if len(hourly) > MAX_HISTORY_POINTS:
            history["hourly"] = hourly[-MAX_HISTORY_POINTS:]

    except Exception as e:
        logger.warning(f"Error updating hourly history: {e}")

    # Update metadata
    history["generated_at"] = datetime.now().isoformat()
    history["total_raw_points"] = len(history.get("hourly", []))

    if history.get("hourly"):
        history["date_range"] = {
            "start": history["hourly"][0]["timestamp"],
            "end": history["hourly"][-1]["timestamp"],
        }

    return history

# ============================================================================
# FILE OPERATIONS (ATOMIC WRITES, BACKUPS)
# ============================================================================

def atomic_write_json(data, output_path):
    """Write JSON atomically: temp file -> validate -> rename."""
    temp_path = output_path.with_suffix('.tmp')

    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Validate
    with open(temp_path, "r", encoding="utf-8") as f:
        json.load(f)

    # Atomic rename
    temp_path.rename(output_path)


def backup_existing(output_path, backup_dir, max_backups=MAX_BACKUPS):
    """Create backup before overwriting."""
    if not output_path.exists():
        return

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"index_{timestamp}.json"
    backup_path = backup_dir / backup_name

    try:
        shutil.copy(output_path, backup_path)
        logger.debug(f"Backup created: {backup_name}")

        # Cleanup old backups
        backups = sorted(backup_dir.glob("index_*.json"))
        if len(backups) > max_backups:
            for old_backup in backups[:-max_backups]:
                old_backup.unlink()
    except Exception as e:
        logger.warning(f"Backup failed: {e}")


def write_health_status(success, wallets_total, wallets_failed, index_score):
    """Write health status file."""
    health_data = {
        "last_run": datetime.now().astimezone().isoformat(),
        "success": success,
        "wallets_total": wallets_total,
        "wallets_failed": wallets_failed,
        "wallets_success": wallets_total - wallets_failed,
        "index_score": index_score,
        "failure_rate": round(wallets_failed / wallets_total, 3) if wallets_total > 0 else 0
    }
    try:
        HEALTH_FILE.write_text(json.dumps(health_data, indent=2))
    except Exception as e:
        logger.warning(f"Failed to write health file: {e}")

# ============================================================================
# GIT PUSH (for static hosting via GitHub)
# ============================================================================

def git_push_data():
    """Commit updated data files and push to GitHub for static hosting."""
    try:
        # Stage only the data files
        subprocess.run(
            ["git", "add", "data/index_latest.json", "data/history.json"],
            cwd=str(BASE_DIR), check=True, capture_output=True
        )

        # Check if there's anything to commit
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(BASE_DIR), capture_output=True
        )
        if result.returncode == 0:
            logger.info("Git: no data changes to commit")
            return

        # Commit with timestamp
        ts = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
        subprocess.run(
            ["git", "commit", "-m", f"data: update index {ts}"],
            cwd=str(BASE_DIR), check=True, capture_output=True
        )

        # Push
        subprocess.run(
            ["git", "push"],
            cwd=str(BASE_DIR), check=True, capture_output=True
        )
        logger.info("Git: data pushed to GitHub")

    except subprocess.CalledProcessError as e:
        logger.warning(f"Git push failed (non-fatal): {e}")
    except Exception as e:
        logger.warning(f"Git push error (non-fatal): {e}")


# ============================================================================
# MAIN GENERATION
# ============================================================================

def generate():
    """Generate index data and update history."""
    logger.info("=" * 50)
    logger.info("HyperIndex Generator - Starting")
    logger.info("=" * 50)

    # Ensure directories exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # Load wallets
    logger.info(f"Loading wallets from {WALLETS_FILE}...")
    wallets = load_wallets()
    logger.info(f"Loaded {len(wallets)} wallets")

    # Build index
    logger.info("Fetching positions from Hyperliquid API...")
    data = build_index(wallets)

    # Calculate stats
    active = data['cohort_stats']['active_wallets']
    total = data['cohort_stats']['total_wallets']
    failed_count = total - active

    # Backup existing
    backup_existing(INDEX_PATH, BACKUP_DIR)

    # Remove internal history data before saving index
    index_output = {k: v for k, v in data.items() if k != "_history_data"}

    # Write index
    atomic_write_json(index_output, INDEX_PATH)
    logger.info(f"Written index: {INDEX_PATH.name}")

    # Update and write history
    history = update_history(data)
    atomic_write_json(history, HISTORY_PATH)
    logger.info(f"Updated history: {len(history.get('hourly', []))} points")

    # Write health status
    write_health_status(
        success=True,
        wallets_total=total,
        wallets_failed=failed_count,
        index_score=data['index_score']
    )

    # Summary
    logger.info(f"Index score: {data['index_score']:.4f}")
    logger.info(f"Assets tracked: {len(data['assets'])}")
    logger.info(f"Cohort equity: ${data['cohort_stats']['total_equity']:,.0f}")
    logger.info("Generation complete!")

    # Push updated data to GitHub (serves static hosting)
    git_push_data()

    return data


def run_scheduled(interval_hours=12):
    """Run on a schedule."""
    logger.info(f"Starting scheduled generation (every {interval_hours}h)")

    while True:
        try:
            generate()
            logger.info(f"Next run in {interval_hours} hours...")
            time.sleep(interval_hours * 3600)
        except KeyboardInterrupt:
            logger.info("Stopped by user.")
            break
        except Exception as e:
            logger.error(f"Generation failed: {e}", exc_info=True)
            write_health_status(success=False, wallets_total=0, wallets_failed=0, index_score=0)
            logger.info("Retrying in 5 minutes...")
            time.sleep(300)

# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HyperIndex Data Generator")
    parser.add_argument("--schedule", action="store_true", help="Run on schedule")
    parser.add_argument("--interval", type=float, default=12, help="Schedule interval in hours (default: 12)")
    args = parser.parse_args()

    if args.schedule:
        run_scheduled(args.interval)
    else:
        generate()
