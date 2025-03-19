import os
import sys
import time
from pathlib import Path

from loguru import logger


# Get project root directory
project_root = Path(__file__).parent.parent

# Create logs directory
logs_dir = project_root / "logs"
logs_dir.mkdir(exist_ok=True)

# Check if a log file was specified
log_file = os.environ.get("SITH_LOG_FILE")

if not log_file:
    # If not specified, check if there's a task ID (from session or workspace directory name)
    task_id = os.environ.get("SITH_TASK_ID", "")

    # Use task ID as log filename, instead of using date-time format
    if task_id:
        # Ensure task ID starts with job_
        if not task_id.startswith("job_"):
            task_id = f"job_{task_id}"
        log_filename = f"{task_id}.log"
    else:
        # If no task ID, use a timestamp to create a job_ID format log filename
        job_id = f"job_{int(time.time())}"
        log_filename = f"{job_id}.log"

    log_file = logs_dir / log_filename
else:
    # Use the specified log file
    log_file = Path(log_file)

# Configure loguru logger
logger.remove()  # Remove default handler
# Add console output
logger.add(
    sys.stderr,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
)
# Add file output
logger.add(
    log_file,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
    rotation="100 MB",
    retention="10 days",
)

# Export configured logger
__all__ = ["logger"]

if __name__ == "__main__":
    logger.info("Starting application")
    logger.debug("Debug message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")

    try:
        raise ValueError("Test error")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
