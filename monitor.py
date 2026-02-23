#!/usr/bin/env python3
"""
HyperIndex Monitor - Terminal Dashboard

Shows live status of the HyperIndex automation with countdown to next run.
Leave running in a terminal window for peace of mind.

Usage:
    python monitor.py

Press Ctrl+C to exit.
"""

import json
import time
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
HEALTH_FILE = DATA_DIR / ".health"
INDEX_FILE = DATA_DIR / "index_latest.json"

# Schedule times (hours in 24h format)
SCHEDULE_HOURS = [0, 6, 12, 18]  # 12am, 6am, 12pm, 6pm

# Display settings
REFRESH_INTERVAL = 30  # seconds
BAR_LENGTH = 40

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
WHITE = "\033[97m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# Border color (use empty string for default terminal color)
BORDER = ""

# ============================================================================
# DATA LOADING
# ============================================================================

def load_health():
    """Load health status from .health file."""
    if not HEALTH_FILE.exists():
        return None
    try:
        with open(HEALTH_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def load_index():
    """Load current index data."""
    if not INDEX_FILE.exists():
        return None
    try:
        with open(INDEX_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

# ============================================================================
# SCHEDULE CALCULATIONS
# ============================================================================

def get_next_run_time():
    """Calculate the next scheduled run time."""
    now = datetime.now()
    today = now.date()

    for hour in SCHEDULE_HOURS:
        scheduled = datetime.combine(today, datetime.min.time().replace(hour=hour))
        if scheduled > now:
            return scheduled

    # Next run is tomorrow at first scheduled hour
    tomorrow = today + timedelta(days=1)
    return datetime.combine(tomorrow, datetime.min.time().replace(hour=SCHEDULE_HOURS[0]))


def get_previous_run_time():
    """Calculate the previous scheduled run time (for progress calculation)."""
    now = datetime.now()
    today = now.date()

    # Check today's hours in reverse
    for hour in reversed(SCHEDULE_HOURS):
        scheduled = datetime.combine(today, datetime.min.time().replace(hour=hour))
        if scheduled <= now:
            return scheduled

    # Previous run was yesterday at last scheduled hour
    yesterday = today - timedelta(days=1)
    return datetime.combine(yesterday, datetime.min.time().replace(hour=SCHEDULE_HOURS[-1]))


def format_duration(seconds):
    """Format seconds as HH:MM:SS."""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_time_friendly(dt):
    """Format datetime as friendly string like '6:00 PM'."""
    return dt.strftime("%-I:%M %p")

# ============================================================================
# DISPLAY HELPERS
# ============================================================================

def fmt_money(n):
    """Format number as money string."""
    if n is None:
        return "--"
    a = abs(n)
    sign = "+" if n > 0 else "-" if n < 0 else ""
    if a >= 1e9:
        return f"{sign}${a/1e9:.1f}B"
    if a >= 1e6:
        return f"{sign}${a/1e6:.1f}M"
    if a >= 1e3:
        return f"{sign}${a/1e3:.1f}K"
    return f"{sign}${a:.0f}"


def progress_bar(progress, length=BAR_LENGTH):
    """Generate a progress bar string."""
    filled = int(length * progress)
    bar = "█" * filled + "░" * (length - filled)
    return bar


def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

# ============================================================================
# MAIN DISPLAY
# ============================================================================

def render_dashboard():
    """Render the full dashboard display."""
    health = load_health()
    index = load_index()

    now = datetime.now()
    next_run = get_next_run_time()
    prev_run = get_previous_run_time()

    # Calculate progress
    total_interval = (next_run - prev_run).total_seconds()
    elapsed = (now - prev_run).total_seconds()
    remaining = (next_run - now).total_seconds()
    progress = min(elapsed / total_interval, 1.0) if total_interval > 0 else 0

    # Build display - fixed width of 66 characters inside borders
    W = 64  # inner width
    lines = []

    # Header
    lines.append(f"╔{'═' * W}╗")
    lines.append(f"║  {GREEN}🟢 HyperIndex Monitor{RESET}".ljust(W + 12) + "║")
    lines.append(f"╠{'═' * W}╣")

    # Last run status
    if health:
        last_run_str = health.get("last_run", "Unknown")
        try:
            last_dt = datetime.fromisoformat(last_run_str.replace("Z", "+00:00"))
            last_run_display = last_dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            last_run_display = last_run_str[:19]

        success = health.get("success", False)
        wallets_ok = health.get("wallets_success", 0)
        wallets_total = health.get("wallets_total", 0)

        if success:
            status = f"{GREEN}✅{RESET} ({wallets_ok}/{wallets_total})"
        else:
            status = f"{RED}❌ Failed{RESET}"

        line = f"  Last Run:   {last_run_display}  {status}"
        lines.append(f"║{line.ljust(W + 14)}║")
    else:
        line = f"  Last Run:   {YELLOW}No data available{RESET}"
        lines.append(f"║{line.ljust(W + 14)}║")

    # Next run
    next_run_display = next_run.strftime("%Y-%m-%d %H:%M:%S")
    next_run_friendly = format_time_friendly(next_run)
    line = f"  Next Run:   {next_run_display}  ({next_run_friendly})"
    lines.append(f"║{line.ljust(W)}║")

    lines.append(f"║{' ' * W}║")

    # Countdown progress bar
    bar = progress_bar(progress)
    remaining_str = format_duration(max(0, remaining))
    pct = progress * 100
    lines.append(f"║  ⏳ Next update in:{' ' * (W - 20)}║")
    bar_line = f"  [{bar}] {pct:5.1f}% - {remaining_str}"
    lines.append(f"║{bar_line.ljust(W)}║")

    lines.append(f"║{' ' * W}║")

    # Current index metrics
    if index:
        score = index.get("index_score", 0)
        stats = index.get("cohort_stats", {})
        leverage = stats.get("L_cohort_total", 0)
        equity = stats.get("total_equity", 0)

        score_color = GREEN if score > 0 else RED if score < 0 else RESET
        score_str = f"{score_color}{score:+.4f}{RESET}"

        lines.append(f"║  📊 Current Index:{' ' * (W - 19)}║")
        metric_line = f"     Score: {score_str}  │  Leverage: {leverage:.2f}x  │  Equity: {fmt_money(equity)}"
        lines.append(f"║{metric_line.ljust(W + 9)}║")
    else:
        lines.append(f"║  📊 Current Index: {YELLOW}No data{RESET}".ljust(W + 12) + "║")

    lines.append(f"║{' ' * W}║")

    # Top 3 positions
    lines.append(f"║  🔥 Top Positions:{' ' * (W - 19)}║")

    if index and "assets" in index:
        assets = sorted(index["assets"], key=lambda a: abs(a.get("net_usd", 0)), reverse=True)[:3]
        for asset in assets:
            name = asset.get("asset", "???")[:5]
            net = asset.get("net_usd", 0)
            tilt = asset.get("tilt", 0) * 100
            conv = abs(asset.get("conv_equity", 0))

            net_color = GREEN if net > 0 else RED
            net_str = f"{net_color}{fmt_money(net):<9}{RESET}"
            tilt_str = f"{tilt:+.0f}%"

            pos_line = f"     {name:<5} {net_str}  (Tilt: {tilt_str:>5})  Conv: {conv:.2f}"
            lines.append(f"║{pos_line.ljust(W + 9)}║")
    else:
        lines.append(f"║     {DIM}No position data available{RESET}".ljust(W + 8) + "║")

    # Footer
    lines.append(f"╚{'═' * W}╝")
    lines.append(f"  {DIM}Press Ctrl+C to exit  │  Updates every {REFRESH_INTERVAL}s  │  {now.strftime('%H:%M:%S')}{RESET}")

    return "\n".join(lines)

# ============================================================================
# MAIN LOOP
# ============================================================================

def main():
    """Main monitor loop."""
    print(f"\n{BOLD}Starting HyperIndex Monitor...{RESET}\n")

    try:
        while True:
            clear_screen()
            print(render_dashboard())
            time.sleep(REFRESH_INTERVAL)
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Monitor stopped.{RESET}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
