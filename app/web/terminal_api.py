import asyncio
import uuid
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from ..tool.bash import Bash

terminal_router = APIRouter(prefix="/api/terminal", tags=["terminal"])

# Store active terminal sessions
active_terminals = {}

@terminal_router.post("/execute")
async def execute_command(request: Request):
    """Execute a terminal command"""
    data = await request.json()
    if not data or 'command' not in data:
        return JSONResponse(content={"error": "No command provided"}, status_code=400)
    
    command = data['command']
    command_id = str(uuid.uuid4())
    
    # Create a new Bash tool instance if not exists
    if command_id not in active_terminals:
        active_terminals[command_id] = Bash()
    
    try:
        # Execute the command
        result = await active_terminals[command_id].execute(command)
        
        # Determine status
        status = "completed"
        if result.get('exit_code') == -1:
            status = "running"  # Command is still running or interactive
        
        # Prepare response
        response = {
            "command_id": command_id,
            "status": status,
            "output": result.get('output', ''),
            "error": result.get('error', '')
        }
        
        # Send terminal update through WebSocket if available
        app = request.app
        if hasattr(app, 'websocket_manager'):
            await app.websocket_manager.broadcast_terminal_update(command_id, response)
            
        return response
    
    except Exception as e:
        return JSONResponse(
            content={
                "command_id": command_id,
                "status": "error",
                "error": str(e)
            },
            status_code=500
        )

@terminal_router.post("/input")
async def send_input(request: Request):
    """Send input to a running command"""
    data = await request.json()
    if not data or 'command_id' not in data or 'input' not in data:
        return JSONResponse(content={"error": "Missing command_id or input"}, status_code=400)
    
    command_id = data['command_id']
    input_text = data['input']
    
    if command_id not in active_terminals:
        return JSONResponse(content={"error": "No active terminal session found"}, status_code=404)
    
    try:
        # Send input to the running command
        result = await active_terminals[command_id].execute(input_text)
        
        # Determine status
        status = "completed"
        if result.get('exit_code') == -1:
            status = "running"
        
        # Prepare response
        response = {
            "command_id": command_id,
            "status": status,
            "output": result.get('output', ''),
            "error": result.get('error', '')
        }
        
        # Send terminal update through WebSocket if available
        app = request.app
        if hasattr(app, 'websocket_manager'):
            await app.websocket_manager.broadcast_terminal_update(command_id, response)
            
        return response
    
    except Exception as e:
        return JSONResponse(
            content={
                "command_id": command_id,
                "status": "error",
                "error": str(e)
            },
            status_code=500
        )

@terminal_router.post("/interrupt")
async def interrupt_command(request: Request):
    """Interrupt a running command with Ctrl+C"""
    data = await request.json()
    if not data or 'command_id' not in data:
        return JSONResponse(content={"error": "No command_id provided"}, status_code=400)
    
    command_id = data['command_id']
    
    if command_id not in active_terminals:
        return JSONResponse(content={"error": "No active terminal session found"}, status_code=404)
    
    try:
        # Send Ctrl+C to interrupt the command
        result = await active_terminals[command_id].execute("ctrl+c")
        
        # Prepare response
        response = {
            "command_id": command_id,
            "status": "interrupted",
            "output": result.get('output', ''),
            "error": result.get('error', '')
        }
        
        # Send terminal update through WebSocket if available
        app = request.app
        if hasattr(app, 'websocket_manager'):
            await app.websocket_manager.broadcast_terminal_update(command_id, response)
            
        return response
    
    except Exception as e:
        return JSONResponse(
            content={
                "command_id": command_id,
                "status": "error",
                "error": str(e)
            },
            status_code=500
        ) 