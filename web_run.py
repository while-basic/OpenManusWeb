import argparse
import os
import pathlib
import sys
import subprocess
import threading

# Add the parent directory to sys.path
parent_dir = pathlib.Path(__file__).parent.resolve()
sys.path.append(str(parent_dir))

import uvicorn
from loguru import logger
from app.agent.memory import MemoryAgent


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


def check_marqo_running(host="localhost", port=8882):
    """Check if Marqo is running."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error(f"Error checking Marqo: {e}")
        return False


def start_marqo_container():
    """Start the Marqo Docker container if not already running."""
    if check_marqo_running():
        logger.info("Marqo is already running")
        return True
    
    try:
        logger.info("Starting Marqo Docker container...")
        subprocess.run(["docker-compose", "up", "-d", "marqo"], check=True)
        
        # Wait for Marqo to be ready
        import time
        for i in range(10):
            if check_marqo_running():
                logger.info("Marqo is now running")
                return True
            logger.info(f"Waiting for Marqo to start... {i+1}/10")
            time.sleep(3)
        
        logger.error("Timeout waiting for Marqo to start")
        return False
    except Exception as e:
        logger.error(f"Error starting Marqo: {e}")
        return False


def process_logs_in_background(memory_agent):
    """Process logs in a background thread."""
    def _process():
        try:
            logger.info("Processing logs in background...")
            count = memory_agent.process_logs()
            logger.info(f"Processed {count} log entries into memory")
        except Exception as e:
            logger.error(f"Error processing logs: {e}")
    
    thread = threading.Thread(target=_process)
    thread.daemon = True
    thread.start()
    return thread


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
    parser.add_argument("--marqo-host", type=str, default="localhost", help="Marqo host")
    parser.add_argument("--marqo-port", type=int, default=8882, help="Marqo port")
    parser.add_argument("--skip-marqo", action="store_true", help="Skip Marqo memory agent initialization")
    args = parser.parse_args()

    # Ensure required directories exist
    ensure_directories()

    # Check for websocket dependencies
    if not check_websocket_dependencies():
        logger.error("Exiting application. Please install the necessary dependencies and try again.")
        return 1

    # Initialize memory agent with Marqo
    if not args.skip_marqo:
        if not start_marqo_container():
            logger.warning("Failed to start Marqo container. Memory features will be disabled.")
        else:
            try:
                marqo_url = f"http://{args.marqo_host}:{args.marqo_port}"
                memory_agent = MemoryAgent(host=marqo_url)
                logger.info(f"Memory agent initialized with Marqo at {marqo_url}")
                
                # Store memory agent in app state
                from app.web.app import app
                app.state.memory_agent = memory_agent
                
                # Process logs in background
                process_logs_in_background(memory_agent)
            except Exception as e:
                logger.error(f"Error initializing memory agent: {e}")

    # Set environment variable to enable auto-open browser
    os.environ["AUTO_OPEN_BROWSER"] = "1"

    # Start the web server
    print(f"🚀 Sith Web application is starting...")
    print(f"Visit http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port} to get started")
    uvicorn.run("app.web.app:app", host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
