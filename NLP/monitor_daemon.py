#!/usr/bin/env python3
"""
monitor_daemon.py
Simple monitoring script for the NLP daemon to track performance and resource usage.
"""

import os
import time
import psutil
import argparse
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
LOG_FILE = SCRIPT_DIR / "daemon.log"

def get_daemon_process():
    """Find the daemon process if it's running."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python' in proc.info['name'].lower() and proc.info['cmdline']:
                cmdline = ' '.join(proc.info['cmdline'])
                if 'daemon.py start' in cmdline:
                    return psutil.Process(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None

def parse_log_stats():
    """Parse the daemon log to extract statistics."""
    if not LOG_FILE.exists():
        return {}
    
    stats = {
        'total_cycles': 0,
        'successful_cycles': 0,
        'failed_cycles': 0,
        'skipped_tickers': 0,
        'processed_tickers': 0,
        'last_cycle_time': None,
        'average_cycle_time': 0,
        'skip_rate': 0
    }
    
    cycle_times = []
    
    try:
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()
        
        for line in lines:
            if 'Starting scraping cycle #' in line:
                stats['total_cycles'] += 1
            elif 'Scraping cycle completed successfully' in line:
                stats['successful_cycles'] += 1
            elif 'Scraping cycle failed' in line:
                stats['failed_cycles'] += 1
            elif 'SKIPPING' in line and 'No new articles' in line:
                stats['skipped_tickers'] += 1
            elif 'Successfully processed sentiment' in line:
                stats['processed_tickers'] += 1
            elif 'completed in' in line and 'seconds' in line:
                # Extract cycle time
                try:
                    time_part = line.split('completed in ')[1].split(' seconds')[0]
                    cycle_times.append(int(time_part))
                except:
                    pass
            elif 'Current skip rate:' in line:
                try:
                    rate_part = line.split('Current skip rate: ')[1].split('%')[0]
                    stats['skip_rate'] = float(rate_part)
                except:
                    pass
        
        if cycle_times:
            stats['average_cycle_time'] = sum(cycle_times) / len(cycle_times)
            stats['last_cycle_time'] = cycle_times[-1]
    
    except Exception as e:
        print(f"Error parsing log: {e}")
    
    return stats

def monitor_daemon():
    """Monitor the daemon and display status."""
    print("NLP Daemon Monitor")
    print("=" * 50)
    
    # Check if daemon is running
    daemon_proc = get_daemon_process()
    
    if daemon_proc:
        print(f"✓ Daemon is RUNNING (PID: {daemon_proc.pid})")
        
        # Get process info
        try:
            cpu_percent = daemon_proc.cpu_percent(interval=1)
            memory_info = daemon_proc.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            print(f"  CPU Usage: {cpu_percent:.1f}%")
            print(f"  Memory Usage: {memory_mb:.1f} MB")
            print(f"  Running since: {datetime.fromtimestamp(daemon_proc.create_time()).strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"  Error getting process info: {e}")
    else:
        print("✗ Daemon is NOT RUNNING")
    
    print()
    
    # Parse log statistics
    stats = parse_log_stats()
    
    if stats['total_cycles'] > 0:
        print("Performance Statistics:")
        print(f"  Total Cycles: {stats['total_cycles']}")
        print(f"  Successful: {stats['successful_cycles']}")
        print(f"  Failed: {stats['failed_cycles']}")
        print(f"  Success Rate: {(stats['successful_cycles']/stats['total_cycles']*100):.1f}%")
        print()
        
        print("Processing Statistics:")
        print(f"  Tickers Processed: {stats['processed_tickers']}")
        print(f"  Tickers Skipped: {stats['skipped_tickers']}")
        if stats['skip_rate'] > 0:
            print(f"  Current Skip Rate: {stats['skip_rate']:.1f}%")
        print()
        
        if stats['average_cycle_time'] > 0:
            print("Timing Statistics:")
            print(f"  Average Cycle Time: {stats['average_cycle_time']:.0f} seconds")
            if stats['last_cycle_time']:
                print(f"  Last Cycle Time: {stats['last_cycle_time']} seconds")
    else:
        print("No cycle statistics available yet.")
    
    # Log file info
    if LOG_FILE.exists():
        log_size = LOG_FILE.stat().st_size / 1024 / 1024  # MB
        print(f"\nLog File: {log_size:.1f} MB")
    
    print(f"\nLast updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def run_synthetic_check(max_log_age_hours: int = 48) -> int:
    """Run a lightweight CI-friendly health check.

    Returns 0 for pass/warn states and 1 for hard-fail states.
    """
    stats = parse_log_stats()
    daemon_proc = get_daemon_process()

    result = {
        "daemon_running": bool(daemon_proc),
        "log_exists": LOG_FILE.exists(),
        "total_cycles": stats.get("total_cycles", 0),
        "successful_cycles": stats.get("successful_cycles", 0),
        "failed_cycles": stats.get("failed_cycles", 0),
        "status": "ok",
        "reasons": [],
    }

    if LOG_FILE.exists():
        age_hours = (time.time() - LOG_FILE.stat().st_mtime) / 3600
        result["log_age_hours"] = round(age_hours, 2)
        if age_hours > float(max_log_age_hours):
            result["status"] = "warn"
            result["reasons"].append(
                f"daemon.log older than {max_log_age_hours}h"
            )
    else:
        result["status"] = "warn"
        result["reasons"].append("daemon.log not found")

    total_cycles = int(result["total_cycles"])
    failed_cycles = int(result["failed_cycles"])
    successful_cycles = int(result["successful_cycles"])
    if total_cycles >= 3 and failed_cycles > successful_cycles:
        result["status"] = "failed"
        result["reasons"].append("failed cycles exceed successful cycles")

    print(result)
    return 1 if result["status"] == "failed" else 0

def main():
    """Main monitoring function."""
    parser = argparse.ArgumentParser(description="Monitor NLP daemon health")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Run CI-friendly synthetic checks and exit with status code",
    )
    parser.add_argument(
        "--max-log-age-hours",
        type=int,
        default=48,
        help="Warn when daemon.log age exceeds this threshold",
    )
    args = parser.parse_args()

    if args.synthetic:
        raise SystemExit(run_synthetic_check(max_log_age_hours=args.max_log_age_hours))

    try:
        monitor_daemon()
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()