"""
Log Monitoring Debug Tool - Test log file reading and WebSocket communication
Usage:
    1. Direct run: python debug_log_monitor.py job_123456
    2. Specify log path: python debug_log_monitor.py job_123456 --log_dir /path/to/logs
"""

import argparse
import json
import sys
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


# Determine project root directory
try:
    # Add project root directory to Python path
    project_root = Path(__file__).parent.parent
    sys.path.append(str(project_root))

    # Import log monitor from the project
    from app.utils.log_monitor import LogFileMonitor
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running this script from the project root or tools directory")
    sys.exit(1)


class DebugEventHandler(FileSystemEventHandler):
    """File system event handler focused on log file changes"""

    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
        self.last_position = 0

    def on_modified(self, event):
        if not event.is_directory and event.src_path == str(self.log_file_path):
            try:
                with open(event.src_path, "r", encoding="utf-8") as file:
                    file.seek(self.last_position)
                    new_content = file.read()
                    if new_content:
                        print(f"\n--- Log change detected ({time.strftime('%H:%M:%S')}) ---")
                        print(f"Content read: {len(new_content)} characters")
                        print(f"Content preview: {new_content[:100]}...")
                    self.last_position = file.tell()
            except Exception as e:
                print(f"Error reading log file: {e}")


def test_log_monitor(job_id, log_dir=None):
    """Test log monitor functionality"""
    if not log_dir:
        log_dir = project_root / "logs"
    else:
        log_dir = Path(log_dir)

    log_file = log_dir / f"{job_id}.log"
    print(f"[Debug] Monitoring log file: {log_file}")

    # Check if log file exists
    if not log_file.exists():
        print(f"[Warning] Log file doesn't exist: {log_file}")
        print(f"Creating empty log file for testing...")
        with open(log_file, "w") as f:
            f.write(f"Test log file created at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Use custom handler to directly monitor file changes
    print("[Debug] Using raw Watchdog to monitor file changes...")
    event_handler = DebugEventHandler(log_file)
    observer = Observer()
    observer.schedule(event_handler, path=str(log_dir), recursive=False)
    observer.start()

    # Test using project's LogFileMonitor
    print("[Debug] Monitoring using project's LogFileMonitor...")
    log_monitor = LogFileMonitor(job_id, str(log_dir))
    log_observer = log_monitor.start_monitoring()

    try:
        # Append some test logs for verification
        print(f"\n[Debug] Writing some test logs to file: {log_file}")
        with open(log_file, "a") as f:
            for i in range(5):
                test_log = f"{time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} | INFO     | test:debug:{i} - Test log #{i+1}\n"
                f.write(test_log)
                f.flush()
                time.sleep(1)

        # Wait for monitoring to process
        time.sleep(2)

        # Check if LogFileMonitor captured logs
        logs = log_monitor.get_log_entries()
        print(f"\n[Debug] Log entries captured by LogFileMonitor: {len(logs)}")
        for i, log in enumerate(logs[-5:] if len(logs) > 5 else logs):
            print(f"  {i+1}. {log}")

        # Simulate WebSocket message
        print("\n[Debug] Simulating WebSocket message...")
        ws_data = {
            "status": "processing",
            "system_logs": logs[-5:] if len(logs) > 5 else logs,
        }
        print(f"JSON message length: {len(json.dumps(ws_data))} bytes")
        print(f"Sample message content: {json.dumps(ws_data, ensure_ascii=False)[:200]}...")

        # Interactive loop, continuously monitor new logs
        print("\n[Debug] Entering monitoring mode, press Enter to continue, 'q' to exit...")
        while True:
            choice = input("Command (Enter to continue, 'a' to add log, 'q' to quit): ")
            if choice.lower() == "q":
                break
            elif choice.lower() == "a":
                # Add new test log
                with open(log_file, "a") as f:
                    test_log = f"{time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} | INFO     | test:debug:{time.time()} - Manually added test log\n"
                    f.write(test_log)
                    print(f"Added test log: {test_log.strip()}")

            # Get latest logs
            new_logs = log_monitor.get_log_entries()
            if len(new_logs) > len(logs):
                print(f"\n[Debug] Detected {len(new_logs) - len(logs)} new logs:")
                for log in new_logs[len(logs) :]:
                    print(f"  • {log}")
                logs = new_logs

    except KeyboardInterrupt:
        print("\n[Debug] User interrupted test")

    finally:
        print("[Debug] Cleaning up resources...")
        observer.stop()
        observer.join()
        log_observer.stop()
        log_observer.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Log Monitoring Debug Tool")
    parser.add_argument("job_id", help="Job ID to monitor, like job_12345")
    parser.add_argument("--log_dir", help="Log directory path", default=None)
    args = parser.parse_args()

    print("=" * 60)
    print(f"Log Monitoring Debug Tool v1.0")
    print(f"Testing job_id: {args.job_id}")
    print(f"Log directory: {args.log_dir if args.log_dir else 'default'}")
    print("=" * 60)

    test_log_monitor(args.job_id, args.log_dir)
