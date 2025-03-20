import asyncio
import json
import os
import threading
import time
import uuid
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    Depends,
)
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from loguru import logger

from app.agent.sith import Sith
from app.flow.base import FlowType
from app.flow.flow_factory import FlowFactory
from app.web.log_handler import capture_session_logs, get_logs
from app.web.log_parser import get_all_logs_info, get_latest_log_info, parse_log_file
from app.web.thinking_tracker import ThinkingTracker
from app.web.terminal_api import terminal_router
from app.web.routes.memory import router as memory_router

# Add a global cache to track memory operations
request_cache = {}

# Control whether to automatically open browser (read from environment variable, default is True)
AUTO_OPEN_BROWSER = os.environ.get("AUTO_OPEN_BROWSER", "1") == "1"
last_opened = False  # Track if browser has been opened

# Get current directory
current_dir = Path(__file__).parent

# Define FastAPI lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the application"""
    # Startup event
    global last_opened
    if AUTO_OPEN_BROWSER and not last_opened:
        # Delay 1 second to ensure service has started
        threading.Timer(1.0, lambda: webbrowser.open("http://localhost:8000")).start()
        print("🌐 Automatically opening browser...")
        last_opened = True
    
    yield  # This is where the application runs
    
    # Shutdown event - add any cleanup code here if needed
    pass

# Create app with lifespan
app = FastAPI(title="Sith Web", lifespan=lifespan)

# Register memory API router
from app.web.routes.memory import router as memory_router
app.include_router(memory_router)

# Mount static files directory
app.mount("/static", StaticFiles(directory=current_dir / "static"), name="static")
# Set templates directory
templates = Jinja2Templates(directory=current_dir / "templates")

# Store active sessions and their results
active_sessions: Dict[str, dict] = {}

# Store task cancellation events
cancel_events: Dict[str, asyncio.Event] = {}

# Store WebSocket connections
websocket_connections: Dict[str, list] = {}

# Create workspace root directory
WORKSPACE_ROOT = Path(__file__).parent.parent.parent / "workspace"
WORKSPACE_ROOT.mkdir(exist_ok=True)

# Logs directory
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Import log monitor
from app.utils.log_monitor import LogFileMonitor


# Store active log monitors
active_log_monitors: Dict[str, LogFileMonitor] = {}


# Function to create workspace directory
def create_workspace(session_id: str) -> Path:
    """Create workspace directory for a session"""
    # Simplify session_id as directory name
    job_id = f"job_{session_id[:8]}"
    workspace_dir = WORKSPACE_ROOT / job_id
    workspace_dir.mkdir(exist_ok=True)
    return workspace_dir


# Request models
class SessionRequest(BaseModel):
    prompt: str


@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/combo", response_class=HTMLResponse)
async def get_combo_page(request: Request):
    """Combined page with chat and memory functionality"""
    return templates.TemplateResponse("index_with_memory.html", {"request": request})


@app.get("/memory", response_class=HTMLResponse)
async def get_memory_page():
    # Read the HTML file
    current_dir = Path(__file__).parent
    with open(current_dir / "static" / "memory_interface.html", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)


@app.post("/api/chat")
async def create_chat_session(
    session_req: SessionRequest, background_tasks: BackgroundTasks
):
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = {
        "status": "processing",
        "result": None,
        "log": [],
        "workspace": None,
    }

    # Create cancellation event
    cancel_events[session_id] = asyncio.Event()

    # Create workspace directory
    workspace_dir = create_workspace(session_id)
    active_sessions[session_id]["workspace"] = str(
        workspace_dir.relative_to(WORKSPACE_ROOT)
    )

    background_tasks.add_task(process_prompt, session_id, session_req.prompt)
    return {
        "session_id": session_id,
        "workspace": active_sessions[session_id]["workspace"],
    }


@app.get("/api/chat/{session_id}")
async def get_chat_result(session_id: str):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # Use new log processing module to get logs
    session = active_sessions[session_id]
    session["log"] = get_logs(session_id)

    return session


@app.post("/api/chat/{session_id}/stop")
async def stop_processing(session_id: str):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    if session_id in cancel_events:
        cancel_events[session_id].set()

    active_sessions[session_id]["status"] = "stopped"
    active_sessions[session_id]["result"] = "Processing stopped by user"

    return {"status": "stopped"}


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    # Add websocket to active_connections
    if session_id not in websocket_connections:
        websocket_connections[session_id] = []
    websocket_connections[session_id].append(websocket)
    
    try:
        # Define a helper function to send WebSocket messages
        async def ws_send(message: str):
            await websocket.send_text(message)
            
        # Add broadcast terminal update method to app, available for terminal_api usage
        app.websocket_manager = type('WebSocketManager', (), {
            'broadcast_terminal_update': 
                lambda cmd_id, data: asyncio.create_task(
                    broadcast_terminal_update(session_id, cmd_id, data)
                )
        })
            
        # Wait for client messages until connection closes
        while True:
            data = await websocket.receive_text()
            print(f"Received message: {data}")
            
    except WebSocketDisconnect:
        # Remove websocket from active_connections
        if session_id in websocket_connections:
            websocket_connections[session_id].remove(websocket)
            if not websocket_connections[session_id]:
                del websocket_connections[session_id]
                
# Broadcast terminal update to all connected clients
async def broadcast_terminal_update(session_id, command_id, data):
    if session_id in websocket_connections:
        message = {
            'type': 'terminal_update',
            'command_id': command_id,
            'output': data.get('output', ''),
            'error': data.get('error', ''),
            'status': data.get('status', '')
        }
        
        for client in websocket_connections[session_id]:
            try:
                await client.send_text(json.dumps(message))
            except Exception as e:
                print(f"Error sending terminal update: {e}")

# New function to broadcast system logs to connected clients
async def broadcast_system_logs(session_id, logs):
    """Send system logs via WebSocket to all connected clients for a session"""
    if session_id in websocket_connections:
        message = {
            'type': 'system_logs',
            'logs': logs
        }
        
        for client in websocket_connections[session_id]:
            try:
                await client.send_text(json.dumps(message))
            except Exception as e:
                print(f"Error sending system logs: {e}")

# Add LLM communication hook
from app.web.thinking_tracker import ThinkingTracker


# Wrapper class for LLM communications
class LLMCommunicationTracker:
    """Track communications with the LLM, using monkey patching instead of callbacks"""

    def __init__(self, session_id: str, agent=None):
        self.session_id = session_id
        self.agent = agent
        self.original_run_method = None

        # If agent is provided, install hooks
        if agent and hasattr(agent, "llm") and hasattr(agent.llm, "completion"):
            self.install_hooks()

    def install_hooks(self):
        """Install hooks to capture LLM communication content"""
        if not self.agent or not hasattr(self.agent, "llm"):
            return False

        # Save original method
        llm = self.agent.llm
        if hasattr(llm, "completion"):
            self.original_completion = llm.completion
            # Replace with our wrapper method
            llm.completion = self._wrap_completion(self.original_completion)
            return True
        return False

    def uninstall_hooks(self):
        """Uninstall hooks, restore original method"""
        if self.agent and hasattr(self.agent, "llm") and self.original_completion:
            self.agent.llm.completion = self.original_completion

    def _wrap_completion(self, original_method):
        """Wrap LLM's completion method to capture input and output"""
        session_id = self.session_id

        async def wrapped_completion(*args, **kwargs):
            # Record input
            prompt = kwargs.get("prompt", "")
            if not prompt and args:
                prompt = args[0]
            if prompt:
                ThinkingTracker.add_communication(
                    session_id,
                    "Sent to LLM",
                    prompt[:500] + ("..." if len(prompt) > 500 else ""),
                )

            # Call original method
            result = await original_method(*args, **kwargs)

            # Record output
            if result:
                content = result
                if isinstance(result, dict) and "content" in result:
                    content = result["content"]
                elif hasattr(result, "content"):
                    content = result.content

                if isinstance(content, str):
                    ThinkingTracker.add_communication(
                        session_id,
                        "Received from LLM",
                        content[:500] + ("..." if len(content) > 500 else ""),
                    )

            return result

        return wrapped_completion


# Import new created LLM wrapper
from app.agent.llm_wrapper import LLMCallbackWrapper


# Modify file API, support workspace directory
@app.get("/api/files")
async def get_generated_files():
    """Get all workspace directories and files"""
    result = []

    # Get all workspace directories
    workspaces = list(WORKSPACE_ROOT.glob("job_*"))
    workspaces.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    for workspace in workspaces:
        workspace_name = workspace.name
        # Get all files in workspace and sort by modification time
        files = []
        with os.scandir(workspace) as it:
            for entry in it:
                if entry.is_file() and entry.name.split(".")[-1] in [
                    "txt",
                    "md",
                    "html",
                    "css",
                    "js",
                    "py",
                    "json",
                ]:
                    files.append(entry)
        # Sort by modification time in descending order
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # If there are files, add the workspace
        if files:
            workspace_item = {
                "name": workspace_name,
                "path": str(workspace.relative_to(Path(__file__).parent.parent.parent)),
                "modified": workspace.stat().st_mtime,
                "files": [],
            }

            # Add files in the workspace
            for file in sorted(files, key=lambda p: p.name):
                workspace_item["files"].append(
                    {
                        "name": file.name,
                        "path": str(
                            Path(file.path).relative_to(
                                Path(__file__).parent.parent.parent
                            )
                        ),
                        "type": Path(file.path).suffix[1:],  # Remove . extension
                        "size": file.stat().st_size,
                        "modified": file.stat().st_mtime,
                    }
                )

            result.append(workspace_item)

    return {"workspaces": result}


# Add new log file interface
@app.get("/api/logs")
async def get_system_logs(limit: int = 10):
    """Get system log list"""
    log_files = []
    for entry in os.scandir(LOGS_DIR):
        if entry.is_file() and entry.name.endswith(".log"):
            log_files.append(
                {
                    "name": entry.name,
                    "size": entry.stat().st_size,
                    "modified": entry.stat().st_mtime,
                }
            )
    # Sort by modification time in descending order and limit quantity
    log_files.sort(key=lambda x: x["modified"], reverse=True)
    return {"logs": log_files[:limit]}


@app.get("/api/logs/{log_name}")
async def get_log_content(log_name: str, parsed: bool = False):
    """Get specific log file content"""
    log_path = LOGS_DIR / log_name
    # Security check
    if not log_path.exists() or not log_path.is_file():
        raise HTTPException(status_code=404, detail="Log file not found")

    # If request parsed log information
    if parsed:
        log_info = parse_log_file(str(log_path))
        log_info["name"] = log_name
        return log_info

    # Otherwise return original content
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {"name": log_name, "content": content}


@app.get("/api/logs_parsed")
async def get_parsed_logs(limit: int = 10):
    """Get parsed log information list"""
    return {"logs": get_all_logs_info(str(LOGS_DIR), limit)}


@app.get("/api/logs_parsed/{log_name}")
async def get_parsed_log(log_name: str):
    """Get parsed information of specific log file"""
    log_path = LOGS_DIR / log_name
    # Security check
    if not log_path.exists() or not log_path.is_file():
        raise HTTPException(status_code=404, detail="Log file not found")

    log_info = parse_log_file(str(log_path))
    log_info["name"] = log_name
    return log_info


@app.get("/api/latest_log")
async def get_latest_log():
    """Get parsed information of latest log file"""
    return get_latest_log_info(str(LOGS_DIR))


@app.get("/api/files/{file_path:path}")
async def get_file_content(file_path: str):
    """Get specific file content"""
    # Security check, prevent directory traversal attack
    root_dir = Path(__file__).parent.parent.parent
    full_path = root_dir / file_path

    # Ensure file is within project directory
    try:
        full_path.relative_to(root_dir)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # Read file content
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Determine file type
        file_type = full_path.suffix[1:] if full_path.suffix else "text"

        return {
            "name": full_path.name,
            "path": file_path,
            "type": file_type,
            "content": content,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


# Modify process_prompt function, handle workspace
async def process_prompt(session_id: str, prompt: str):
    """Process a user prompt, handling the entire workflow from prompt to result."""
    # Create a unique request ID to prevent duplicates
    request_id = f"{session_id}:{prompt[:20]}"
    
    # Check if we've already processed this exact request
    global request_cache
    if request_id in request_cache:
        logger.warning(f"Duplicate request detected: {request_id}")
        return
    
    # Mark this request as being processed
    request_cache[request_id] = {"status": "processing", "timestamp": time.time()}
    
    # Get session workspace
    workspace_path = None
    if session_id in active_sessions and active_sessions[session_id].get("workspace"):
        workspace_name = active_sessions[session_id]["workspace"]
        workspace_path = WORKSPACE_ROOT / workspace_name

    # Start log capture for this session
    with capture_session_logs(session_id) as log_capture:
        # Set up thinking tracker
        ThinkingTracker.start_tracking(session_id)

        # Setup result
        result = None
        has_error = False
        sync_task = None

        try:
            # Set up log file monitoring
            log_handler = SimpleLogHandler(session_id)

            # Create Sith agent
            agent = Sith()
            
            # Store user query in memory if available, with duplicate prevention
            memory_agent = getattr(app.state, "memory_agent", None)
            if memory_agent:
                try:
                    # Simple cache check
                    memory_key = f"memory:{session_id}:{prompt[:30]}"
                    if memory_key not in request_cache:
                        request_cache[memory_key] = True
                        memory_agent.add_memory({
                            "content": prompt,
                            "source": "user_query",
                            "metadata": {
                                "session_id": session_id,
                                "timestamp": time.time(),
                            }
                        })
                        logger.info(f"Stored user query in memory: {prompt[:50]}...")
                    else:
                        logger.warning(f"Skipping duplicate memory addition: {memory_key}")
                except Exception as e:
                    logger.error(f"Failed to store user query in memory: {e}")

            # Setup communication hooks
            from app.web.llm_monitor import LLMMonitor
            llm_monitor = LLMMonitor()
            
            # Use workspace name as log file name prefix
            job_id = workspace_path.name
            # Set log file path
            task_log_path = LOGS_DIR / f"{job_id}.log"

            # Create log monitor and start monitoring
            log_monitor = LogFileMonitor(job_id)
            observer = log_monitor.start_monitoring()
            active_log_monitors[session_id] = log_monitor

            async def sync_logs():
                """Periodically get logs from LogFileMonitor and update to ThinkingTracker in real time"""
                last_count = 0
                try:
                    while True:
                        if session_id not in active_log_monitors:
                            break
                        current_logs = active_log_monitors[session_id].get_log_entries()
                        if len(current_logs) > last_count:
                            # Process new log entries
                            new_logs = current_logs[last_count:]
                            # Process each new log entry immediately, ensure real-time
                            for log_entry in new_logs:
                                # Process each log entry individually, immediately add to ThinkingTracker
                                ThinkingTracker.add_log_entry(
                                    session_id,
                                    {
                                        "level": log_entry.get("level", "INFO"),
                                        "message": log_entry.get("message", ""),
                                        "timestamp": log_entry.get("timestamp", time.time()),
                                    },
                                )
                            
                            # Also send the new logs via WebSocket
                            log_texts = [f"{entry.get('timestamp', '')} | {entry.get('level', 'INFO')} | {entry.get('message', '')}" 
                                        for entry in new_logs]
                            await broadcast_system_logs(session_id, log_texts)
                            
                            last_count = len(current_logs)
                        # Reduce polling interval, improve real-time
                        await asyncio.sleep(0.1)  # Check every 0.1 seconds
                except Exception as e:
                    print(f"Error synchronizing logs: {str(e)}")

            # Start log synchronization task
            sync_task = asyncio.create_task(sync_logs())

            # Set environment variable to inform logger to use this log file, ensure both ways are set
            os.environ["SITH_LOG_FILE"] = str(task_log_path)
            os.environ["SITH_TASK_ID"] = job_id

            # Initialize thinking tracking
            ThinkingTracker.add_thinking_step(session_id, "Start processing user request")
            ThinkingTracker.add_thinking_step(
                session_id, f"Workspace directory: {workspace_path.name}"
            )

            # Directly record user input prompt
            ThinkingTracker.add_communication(session_id, "User input", prompt)

            # Initialize agent and task flow
            ThinkingTracker.add_thinking_step(session_id, "Initialize AI agent and task flow")

            # Use wrapper to wrap LLM
            if hasattr(agent, "llm"):
                original_llm = agent.llm
                wrapped_llm = LLMCallbackWrapper(original_llm)

                # Register callback functions
                def on_before_request(data):
                    # Extract request content
                    prompt_content = None
                    if data.get("args") and len(data["args"]) > 0:
                        prompt_content = str(data["args"][0])
                    elif data.get("kwargs") and "prompt" in data["kwargs"]:
                        prompt_content = data["kwargs"]["prompt"]
                    else:
                        prompt_content = str(data)

                    # Record communication content
                    print(f"Sent to LLM: {prompt_content[:100]}...")
                    ThinkingTracker.add_communication(
                        session_id, "Sent to LLM", prompt_content
                    )

                def on_after_request(data):
                    # Extract response content
                    response = data.get("response", "")
                    response_content = ""

                    # Try to extract text content from different formats
                    if isinstance(response, str):
                        response_content = response
                    elif isinstance(response, dict):
                        if "content" in response:
                            response_content = response["content"]
                        elif "text" in response:
                            response_content = response["text"]
                        else:
                            response_content = str(response)
                    elif hasattr(response, "content"):
                        response_content = response.content
                    else:
                        response_content = str(response)

                    # Record communication content
                    print(f"Received from LLM: {response_content[:100]}...")
                    ThinkingTracker.add_communication(
                        session_id, "Received from LLM", response_content
                    )

                # Register callback
                wrapped_llm.register_callback("before_request", on_before_request)
                wrapped_llm.register_callback("after_request", on_after_request)

                # Replace original LLM
                agent.llm = wrapped_llm

            flow = FlowFactory.create_flow(
                flow_type=FlowType.PLANNING,
                agents=agent,
            )

            # Record processing start
            ThinkingTracker.add_thinking_step(
                session_id, f"Analyze user request: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
            )
            log_capture.info(f"Start executing: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")

            # Check if task is canceled
            cancel_event = cancel_events.get(session_id)
            if cancel_event and cancel_event.is_set():
                log_capture.warning("Processing canceled by user")
                ThinkingTracker.mark_stopped(session_id)
                active_sessions[session_id]["status"] = "stopped"
                active_sessions[session_id]["result"] = "Processing stopped by user"
                return

            # Check existing files in workspace before execution
            existing_files = set()
            for ext in ["*.txt", "*.md", "*.html", "*.css", "*.js", "*.py", "*.json"]:
                existing_files.update(f.name for f in workspace_path.glob(ext))

            # Track plan creation process
            ThinkingTracker.add_thinking_step(session_id, "Create task execution plan")
            ThinkingTracker.add_thinking_step(session_id, "Start executing task plan")

            # Get cancel event to pass to flow.execute
            cancel_event = cancel_events.get(session_id)

            # Initial check, if already canceled then do not execute
            if cancel_event and cancel_event.is_set():
                log_capture.warning("Processing canceled by user")
                ThinkingTracker.mark_stopped(session_id)
                active_sessions[session_id]["status"] = "stopped"
                active_sessions[session_id]["result"] = "Processing stopped by user"
                return

            # Execute actual processing - pass job_id and cancel_event to flow.execute method
            result = await flow.execute(prompt, job_id, cancel_event)

            # Check newly generated files after execution
            new_files = set()
            for ext in ["*.txt", "*.md", "*.html", "*.css", "*.js", "*.py", "*.json"]:
                new_files.update(f.name for f in workspace_path.glob(ext))
            newly_created = new_files - existing_files

            if newly_created:
                files_list = ", ".join(newly_created)
                ThinkingTracker.add_thinking_step(
                    session_id,
                    f"Generated {len(newly_created)} files in workspace {workspace_path.name}: {files_list}",
                )
                # Also add file list to session result
                active_sessions[session_id]["generated_files"] = list(newly_created)

            # Record completion status
            log_capture.info("Processing completed")
            ThinkingTracker.add_conclusion(
                session_id, f"Task processing completed! Results generated in workspace {workspace_path.name}."
            )

            # Store result in memory if available, with duplicate prevention
            if memory_agent and result:
                try:
                    result_key = f"result:{session_id}:{result[:30]}"
                    if result_key not in request_cache:
                        request_cache[result_key] = True
                        memory_agent.add_memory({
                            "content": result,
                            "source": "agent_response",
                            "metadata": {
                                "session_id": session_id,
                                "timestamp": time.time(),
                                "for_query": prompt[:100] + ("..." if len(prompt) > 100 else "")
                            }
                        })
                        logger.info(f"Stored agent response in memory: {result[:50]}...")
                    else:
                        logger.warning(f"Skipping duplicate result memory addition: {result_key}")
                except Exception as e:
                    logger.error(f"Failed to store agent response in memory: {e}")

            # Return the results
            active_sessions[session_id]["status"] = "completed"
            active_sessions[session_id]["result"] = result
            active_sessions[session_id][
                "thinking_steps"
            ] = ThinkingTracker.get_thinking_steps(session_id)

        except asyncio.CancelledError:
            # Handle cancellation
            print("Processing canceled")
            ThinkingTracker.mark_stopped(session_id)
            active_sessions[session_id]["status"] = "stopped"
            active_sessions[session_id]["result"] = "Processing canceled"
        except Exception as e:
            # Handle error
            error_msg = f"Processing error: {str(e)}"
            print(error_msg)
            ThinkingTracker.add_error(session_id, f"Processing encountered error: {str(e)}")
            active_sessions[session_id]["status"] = "error"
            active_sessions[session_id]["result"] = f"Error: {str(e)}"
        finally:
            # Restore original working directory
            os.chdir(os.getcwd())

            # Clear log file environment variable
            if "SITH_LOG_FILE" in os.environ:
                del os.environ["SITH_LOG_FILE"]
            if "SITH_TASK_ID" in os.environ:
                del os.environ["SITH_TASK_ID"]

            # Clean up resources
            if (
                "agent" in locals()
                and hasattr(agent, "llm")
                and isinstance(agent.llm, LLMCallbackWrapper)
            ):
                try:
                    # Properly remove callback
                    if "on_before_request" in locals():
                        agent.llm._callbacks["before_request"].remove(on_before_request)
                    if "on_after_request" in locals():
                        agent.llm._callbacks["after_request"].remove(on_after_request)
                except (ValueError, Exception) as e:
                    print(f"Error cleaning up callback: {str(e)}")

            # Clean up cancel event
            if session_id in cancel_events:
                del cancel_events[session_id]

            # If monitor exists, stop monitoring
            if session_id in active_log_monitors:
                observer.stop()
                observer.join(timeout=1)
                del active_log_monitors[session_id]

            # Cancel log synchronization task
            if sync_task:
                sync_task.cancel()
                try:
                    await sync_task
                except asyncio.CancelledError:
                    pass
            
    # After the with block completes, clear this request from the cache after a while
    cache_cleanup_time = 300  # 5 minutes
    request_cache[request_id]["status"] = "completed"
    
    # Start a background task to clear this entry from cache
    async def clear_cache_entry():
        await asyncio.sleep(cache_cleanup_time)
        if request_id in request_cache:
            del request_cache[request_id]
    
    asyncio.create_task(clear_cache_entry())


# Simple log handler class
class SimpleLogHandler:
    def __init__(self, session_id: str):
        self.session_id = session_id
        
    def info(self, message: str):
        logger.info(message)
        
    def warning(self, message: str):
        logger.warning(message)
        
    def error(self, message: str):
        logger.error(message)
        
    def debug(self, message: str):
        logger.debug(message)


# Add new API endpoint to get thinking steps
@app.get("/api/thinking/{session_id}")
async def get_thinking_steps(session_id: str, start_index: int = 0):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "status": ThinkingTracker.get_status(session_id),
        "thinking_steps": ThinkingTracker.get_thinking_steps(session_id, start_index),
    }


# Add API endpoint to get progress information
@app.get("/api/progress/{session_id}")
async def get_progress(session_id: str):
    """Get progress information for a specific session"""
    return ThinkingTracker.get_progress(session_id)


# Add API endpoint to get system logs for a specific session
@app.get("/api/systemlogs/{session_id}")
async def get_system_logs(session_id: str):
    """Get system logs for a specific session"""
    # If session_id is in active_log_monitors, get logs from the monitor
    if session_id in active_log_monitors:
        logs = active_log_monitors[session_id].get_log_entries()
        return {"logs": logs}
    
    # Otherwise read logs directly from the log file
    log_path = LOGS_DIR / f"{session_id}.log"
    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            return {"logs": [line.strip() for line in f.readlines()]}
    
    return {"logs": []}


# Add memory-related models
class MemoryQuery(BaseModel):
    query: str
    limit: int = 5


class MemoryAddRequest(BaseModel):
    content: str
    source: str
    metadata: Optional[Dict] = None


# Function to get memory agent from app state
async def get_memory_agent():
    """Get or create the memory agent.
    
    This function is used as a FastAPI dependency to provide the memory agent
    to routes that need it.
    """
    if not hasattr(app.state, "memory_agent"):
        from app.agent.memory import MemoryAgent
        app.state.memory_agent = MemoryAgent(
            index_name="openmanus_memory",
            host="http://localhost:8882"
        )
    return app.state.memory_agent


# Add API endpoints for memory queries
@app.post("/api/memory/query")
async def query_memory(query: MemoryQuery, memory_agent=Depends(get_memory_agent)):
    """Query the memory database for relevant information"""
    try:
        results = memory_agent.query_memory(query.query, limit=query.limit)
        return {"results": results}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to query memory: {str(e)}"}
        )


@app.post("/api/memory/add")
async def add_memory(memory: MemoryAddRequest, memory_agent=Depends(get_memory_agent)):
    """Add a new memory item to the database"""
    try:
        doc_id = memory_agent.add_memory({
            "content": memory.content,
            "source": memory.source,
            "metadata": memory.metadata or {}
        })
        return {"success": True, "id": doc_id}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to add memory: {str(e)}"}
        )


@app.get("/api/memory/status")
async def memory_status(memory_agent=Depends(get_memory_agent)):
    """Get memory agent status"""
    try:
        return {
            "status": "available",
            "host": memory_agent.host,
            "index": memory_agent.index_name
        }
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}
