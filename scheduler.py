#!/usr/bin/env python3
"""
HyperIndex Scheduler - Reliable 4x daily updates

Runs as a persistent daemon and triggers generator.py at scheduled times.
More reliable than LaunchAgent StartCalendarInterval.

Usage:
    python3 scheduler.py
"""

import subprocess
import time
import logging
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "logs" / "scheduler.log"
GENERATOR_SCRIPT = BASE_DIR / "generator.py"

SCHEDULE_HOURS = [0, 6, 12, 18]  # 12am, 6am, 12pm, 6pm
CHECK_INTERVAL = 60  # Check every 60 seconds

# Track last run to avoid double-runs
last_run_hour = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_generator():
    """Run the generator (which also updates history internally)."""
    logger.info("=" * 50)
    logger.info("SCHEDULED RUN TRIGGERED")
    logger.info("=" * 50)

    try:
        logger.info("Running generator.py...")
        result = subprocess.run(
            ["python3", str(GENERATOR_SCRIPT)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            logger.info("Generator completed successfully")
        else:
            logger.error(f"Generator failed: {result.stderr}")

    except Exception as e:
        logger.error(f"Error during scheduled run: {e}")


def main():
    global last_run_hour

    logger.info("HyperIndex Scheduler starting...")
    logger.info(f"Schedule: {SCHEDULE_HOURS} (hours)")
    logger.info(f"Check interval: {CHECK_INTERVAL}s")

    while True:
        try:
            now = datetime.now()
            current_hour = now.hour
            current_minute = now.minute

            # Check if it's a scheduled hour and we haven't run this hour yet
            if current_hour in SCHEDULE_HOURS and current_hour != last_run_hour:
                # Run within first 5 minutes of the hour
                if current_minute < 5:
                    logger.info(f"Schedule triggered: {now.strftime('%Y-%m-%d %H:%M')}")
                    run_generator()
                    last_run_hour = current_hour

            # Reset last_run_hour when we're past the schedule windows
            if current_hour not in SCHEDULE_HOURS:
                last_run_hour = None

        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
