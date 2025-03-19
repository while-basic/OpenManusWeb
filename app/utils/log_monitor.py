import os
import re
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class LogFileMonitor:
    def __init__(self, job_id=None, log_dir="logs"):
        # Prioritize using task ID from environment variables
        self.job_id = job_id or os.environ.get("SITH_TASK_ID")
        self.log_dir = log_dir

        # Prioritize using log file path from environment variables
        env_log_file = os.environ.get("SITH_LOG_FILE")
        if env_log_file and os.path.exists(env_log_file):
            self.log_file = env_log_file
        else:
            self.log_file = os.path.join(log_dir, f"{self.job_id}.log")

        self.generated_files = []
        self.log_entries = []
        self.file_pattern = re.compile(r"Content successfully saved to (.+)")
        self.last_update_time = 0

    def start_monitoring(self):
        # Ensure log file directory exists
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        # If log file already exists, read existing content first
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r", encoding="utf-8") as file:
                    for line in file:
                        self.parse_log_line(line.strip())
            except Exception as e:
                print(f"Error reading existing log file: {e}")

        # Create observer to monitor changes to the log file
        event_handler = LogEventHandler(self)
        observer = Observer()
        observer.schedule(event_handler, self.log_dir, recursive=False)
        observer.start()
        return observer

    def parse_log_line(self, line):
        # Parse log line
        self.log_entries.append(line)
        self.last_update_time = time.time()

        # Check if there are generated files
        file_match = self.file_pattern.search(line)
        if file_match:
            filename = file_match.group(1)
            if filename not in self.generated_files:
                self.generated_files.append(filename)

    def get_generated_files(self):
        return self.generated_files

    def get_log_entries(self):
        return self.log_entries

    def get_new_entries_since(self, timestamp):
        """Get new log entries after the specified timestamp"""
        if not self.log_entries:
            return []

        # If no new entries, return empty list
        if self.last_update_time <= timestamp:
            return []

        # Find newly added entries
        new_entries = []
        for i in range(len(self.log_entries) - 1, -1, -1):
            # Simplified handling, assuming all new entries are added consecutively
            # Actual implementation may need to add timestamps to log entries
            if i >= len(self.log_entries) - 10:  # Return at most the latest 10 entries
                new_entries.insert(0, self.log_entries[i])
            else:
                break

        return new_entries


class LogEventHandler(FileSystemEventHandler):
    def __init__(self, monitor):
        self.monitor = monitor
        self.last_position = 0

    def on_modified(self, event):
        if not event.is_directory and event.src_path == self.monitor.log_file:
            try:
                with open(event.src_path, "r", encoding="utf-8") as file:
                    file.seek(self.last_position)
                    for line in file:
                        self.monitor.parse_log_line(line.strip())
                    self.last_position = file.tell()
            except Exception as e:
                print(f"Error reading modified log file: {e}")

    def on_created(self, event):
        # If this is a newly created target log file
        if not event.is_directory and event.src_path == self.monitor.log_file:
            try:
                with open(event.src_path, "r", encoding="utf-8") as file:
                    for line in file:
                        self.monitor.parse_log_line(line.strip())
                    self.last_position = file.tell()
            except Exception as e:
                print(f"Error reading newly created log file: {e}")
