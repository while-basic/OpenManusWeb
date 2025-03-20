from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
import traceback
from loguru import logger

from app.agent.memory import MemoryAgent

router = APIRouter(prefix="/api/memory", tags=["memory"])

class MemoryResponse(BaseModel):
    id: str
    content: str
    source: str
    timestamp: str
    metadata: Dict
    score: Optional[float] = None

class MemoryCreateRequest(BaseModel):
    content: str
    source: str = "web_interface"
    metadata: Dict = {}

class MemorySearchRequest(BaseModel):
    query: str
    limit: int = 10

# Global memory agent cache
_memory_agent = None

async def get_memory_agent():
    """Get the memory agent."""
    global _memory_agent
    if _memory_agent is None:
        try:
            logger.info("Initializing memory agent with sith_memory index")
            _memory_agent = MemoryAgent(
                index_name="sith_memory",
                host="http://localhost:8882"
            )
            logger.info("Memory agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize memory agent: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    return _memory_agent

@router.get("/", response_model=List[MemoryResponse])
async def list_memories(
    request: Request,
    limit: int = Query(20, gt=0, le=100),
    memory_agent: MemoryAgent = Depends(get_memory_agent)
):
    """List most recent memories."""
    client_host = request.client.host if request.client else "unknown"
    logger.info(f"List memories request from {client_host} with limit {limit}")
    
    try:
        # This is a simple implementation that just returns recent items
        # In a real implementation, you might want to add pagination, filtering, etc.
        logger.debug(f"Querying memory with limit {limit}")
        results = memory_agent.query_memory("*", limit=limit)
        logger.info(f"Found {len(results)} memories")
        
        formatted_results = []
        for item in results:
            formatted_results.append(MemoryResponse(
                id=item.get("_id", ""),
                content=item.get("content", ""),
                source=item.get("source", "unknown"),
                timestamp=item.get("timestamp", ""),
                metadata=item.get("metadata", {}),
                score=item.get("_score")
            ))
        
        return formatted_results
    except Exception as e:
        logger.error(f"Error listing memories: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error listing memories: {str(e)}")

@router.post("/search", response_model=List[MemoryResponse])
async def search_memories(
    request: Request,
    search_request: MemorySearchRequest,
    memory_agent: MemoryAgent = Depends(get_memory_agent)
):
    """Search memories using vector similarity."""
    client_host = request.client.host if request.client else "unknown"
    logger.info(f"Search memories request from {client_host} for query: {search_request.query}")
    
    try:
        results = memory_agent.query_memory(
            query=search_request.query,
            limit=search_request.limit
        )
        logger.info(f"Search found {len(results)} results for query: {search_request.query}")
        
        formatted_results = []
        for item in results:
            formatted_results.append(MemoryResponse(
                id=item.get("_id", ""),
                content=item.get("content", ""),
                source=item.get("source", "unknown"),
                timestamp=item.get("timestamp", ""),
                metadata=item.get("metadata", {}),
                score=item.get("_score")
            ))
        
        return formatted_results
    except Exception as e:
        logger.error(f"Error searching memories: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error searching memories: {str(e)}")

@router.post("/", response_model=Dict)
async def create_memory(
    request: Request,
    memory_request: MemoryCreateRequest,
    memory_agent: MemoryAgent = Depends(get_memory_agent)
):
    """Create a new memory."""
    client_host = request.client.host if request.client else "unknown"
    logger.info(f"Create memory request from {client_host}")
    logger.debug(f"Memory content: {memory_request.content[:50]}...")
    logger.debug(f"Memory source: {memory_request.source}")
    logger.debug(f"Memory metadata: {memory_request.metadata}")
    
    try:
        # Ensure metadata has numeric values for importance if present
        if "importance" in memory_request.metadata and isinstance(memory_request.metadata["importance"], str):
            try:
                # Convert string importance to integer
                if memory_request.metadata["importance"].lower() == "high":
                    memory_request.metadata["importance"] = 10
                elif memory_request.metadata["importance"].lower() == "medium":
                    memory_request.metadata["importance"] = 5
                elif memory_request.metadata["importance"].lower() == "low":
                    memory_request.metadata["importance"] = 1
                else:
                    # Try to convert to int
                    memory_request.metadata["importance"] = int(memory_request.metadata["importance"])
            except ValueError:
                # Default to 5 if conversion fails
                memory_request.metadata["importance"] = 5
                
        doc_id = memory_agent.add_memory({
            "content": memory_request.content,
            "source": memory_request.source,
            "metadata": memory_request.metadata
        })
        logger.info(f"Memory created successfully with ID: {doc_id}")
        return {"id": doc_id, "success": True}
    except Exception as e:
        logger.error(f"Failed to create memory: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to create memory: {str(e)}")

@router.delete("/{memory_id}", response_model=Dict)
async def delete_memory(
    request: Request,
    memory_id: str,
    memory_agent: MemoryAgent = Depends(get_memory_agent)
):
    """Delete a memory by ID."""
    client_host = request.client.host if request.client else "unknown"
    logger.info(f"Delete memory request from {client_host} for ID: {memory_id}")
    
    try:
        success = memory_agent.delete_memory(memory_id)
        if not success:
            logger.warning(f"Memory with ID {memory_id} not found or could not be deleted")
            raise HTTPException(status_code=404, detail=f"Memory with ID {memory_id} not found or could not be deleted")
        
        logger.info(f"Memory with ID {memory_id} deleted successfully")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting memory: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error deleting memory: {str(e)}") 