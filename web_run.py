import argparse
import os
import pathlib
import sys

# Add the parent directory to sys.path
parent_dir = pathlib.Path(__file__).parent.resolve()
sys.path.append(str(parent_dir))

import uvicorn
from loguru import logger


def check_websocket_dependencies():
    """Check if necessary dependencies for websocket functionality are installed."""
    try:
        import websockets
        import aiofiles
        return True
    except ImportError as e:
        logger.error(f"Missing dependency: {str(e)}")
        logger.error("Please install required dependencies with: pip install websockets aiofiles")
        return False


def ensure_directories():
    """Ensure required directories exist."""
    # Create the necessary directories
    os.makedirs("logs", exist_ok=True)
    os.makedirs("workspace", exist_ok=True)
    os.makedirs("reports", exist_ok=True)


def main():
    """Run the web server."""
    parser = argparse.ArgumentParser(description="Sith Web Application Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on")
    args = parser.parse_args()

    # Ensure required directories exist
    ensure_directories()

    # Check for websocket dependencies
    if not check_websocket_dependencies():
        logger.error("Exiting application. Please install the necessary dependencies and try again.")
        return 1

    # Set environment variable to enable auto-open browser
    os.environ["AUTO_OPEN_BROWSER"] = "1"

    # Start the web server
    print(f"🚀 Sith Web application is starting...")
    print(f"Visit http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port} to get started")
    uvicorn.run("app.web.app:app", host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
