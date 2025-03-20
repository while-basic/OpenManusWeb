# Memory Agent

The Memory Agent is a component that enables persistent storage and retrieval of information across sessions using Marqo vector database.

## Overview

The Memory Agent provides a shared "brain" for all agents in the system, allowing them to:

- Store important information for future use
- Retrieve contextually relevant information based on semantic queries
- Build upon past interactions without starting from scratch
- Process and extract information from logs

## Architecture

The Memory Agent is built on:

1. **Marqo Vector Database**: A Docker-based vector database for efficient semantic search
2. **MemoryAgent Class**: Handles interfacing with the database
3. **MemoryTool**: Provides tools to the Sith agent to interact with memory
4. **API Endpoints**: Allow direct access to memory functions via web API

## Setup and Usage

### Prerequisites

- Docker and Docker Compose installed
- Python 3.8+ environment with required packages

### Starting the Memory Agent

The Memory Agent is automatically initialized when running the web application:

```bash
python web_run.py
```

This will:
1. Start the Marqo Docker container if not already running
2. Initialize the memory agent connected to Marqo
3. Process existing logs to extract information
4. Make memory functionality available to the agent

### Command Line Options

The following command line options are available:

- `--marqo-host`: Specify Marqo host (default: localhost)
- `--marqo-port`: Specify Marqo port (default: 8882)
- `--skip-marqo`: Skip Marqo initialization

Example:
```bash
python web_run.py --marqo-host myhost --marqo-port 8899
```

### API Endpoints

The following API endpoints are available for direct memory interaction:

- `POST /api/memory/query`: Query the memory database
- `POST /api/memory/add`: Add a new memory item
- `GET /api/memory/status`: Check memory agent status

## Using Memory in Agents

The Sith agent has been enhanced with memory capabilities through the `MemoryTool`. This tool provides two main functions:

1. `search`: Find relevant information in memory
2. `store`: Save important information to memory

Example usage (from within agent):

```
# Search memory for relevant information about "python errors"
memory_results = memory.search(query="python errors", limit=5)

# Store important information in memory
memory.store(content="The user prefers dark theme in the UI", 
             source="user_preference",
             metadata={"theme": "dark"})
```

## Data Structure

Each memory item contains:

- **content**: The main text content of the memory
- **source**: Where the memory came from (e.g., "user_input", "logs", "agent")
- **timestamp**: When the memory was created
- **metadata**: Additional structured data about the memory

## Docker Setup

The Marqo vector database runs in a Docker container defined in `docker-compose.yml`. The container is configured to:

- Use port 8882
- Persist data in a Docker volume
- Automatically restart unless explicitly stopped

## Troubleshooting

If memory features are not working:

1. Check that Docker is running
2. Verify the Marqo container is running: `docker ps | grep marqo`
3. Check application logs for memory-related errors
4. Test the memory API directly: `curl http://localhost:8000/api/memory/status` 