from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field

from app.tool.base import BaseTool
from app.logger import logger


class MemorySearchInput(BaseModel):
    """Input for the memory search tool."""
    query: str = Field(
        ..., description="Query to search for in the memory database"
    )
    limit: int = Field(
        5, description="Maximum number of results to return"
    )


class MemoryStoreInput(BaseModel):
    """Input for the memory store tool."""
    content: str = Field(
        ..., description="Content to store in memory"
    )
    source: str = Field(
        "agent", description="Source of the memory (e.g., 'user', 'agent', 'web')"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata for the memory"
    )


class MemoryTool(BaseTool):
    """Tool for storing and retrieving information from the memory database."""
    
    name: str = "memory"
    description: str = (
        "This tool enables storing and retrieving information from the agent's memory. "
        "Use it to remember important facts, retrieve relevant context, or recall previous "
        "interactions. The memory persists across conversations and sessions."
    )
    
    def __init__(self):
        """Initialize the memory tool."""
        super().__init__()
    
    @property
    def _memory_agent(self):
        """Get the memory agent from the app state.
        
        This is a property to lazily load the memory agent when needed.
        """
        from fastapi import HTTPException
        
        # Import app from web module
        try:
            from app.web.app import app
            if hasattr(app.state, "memory_agent"):
                return app.state.memory_agent
            else:
                raise ValueError("Memory agent not available in app state")
        except (ImportError, ValueError) as e:
            logger.error(f"Failed to get memory agent: {e}")
            raise HTTPException(status_code=503, detail="Memory agent not available")
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the memory tool with the given parameters.
        
        This method implements the abstract method from BaseTool.
        It determines which operation to perform based on the parameters.
        
        Args:
            action: The action to perform, either "search" or "store"
            query: The search query (for search action)
            content: The content to store (for store action)
            source: The source of the memory (for store action)
            metadata: Additional metadata (for store action)
            limit: Maximum number of results to return (for search action)
            
        Returns:
            Results of the operation
        """
        # Determine which action to perform
        action = kwargs.get("action", "search")
        
        if action == "search":
            # Handle search operation
            search_input = MemorySearchInput(
                query=kwargs.get("query", ""),
                limit=kwargs.get("limit", 5)
            )
            return await self.search(search_input)
        
        elif action == "store":
            # Handle store operation
            store_input = MemoryStoreInput(
                content=kwargs.get("content", ""),
                source=kwargs.get("source", "agent"),
                metadata=kwargs.get("metadata")
            )
            return await self.store(store_input)
        
        else:
            # Invalid action
            return {
                "error": f"Unknown action: {action}",
                "valid_actions": ["search", "store"]
            }
    
    async def search(self, input_data: MemorySearchInput) -> Dict[str, Any]:
        """Search for information in memory.
        
        Args:
            input_data: Search query and parameters
            
        Returns:
            Results from memory matching the query
        """
        logger.info(f"Searching memory: {input_data.query}")
        try:
            results = self._memory_agent.query_memory(
                query=input_data.query,
                limit=input_data.limit
            )
            
            return {
                "results": results,
                "count": len(results),
                "query": input_data.query
            }
        except Exception as e:
            logger.error(f"Memory search error: {e}")
            return {
                "error": str(e),
                "results": [],
                "count": 0,
                "query": input_data.query
            }
    
    async def store(self, input_data: MemoryStoreInput) -> Dict[str, Any]:
        """Store information in memory.
        
        Args:
            input_data: Content and metadata to store
            
        Returns:
            Success status and ID of the stored memory
        """
        logger.info(f"Storing memory: {input_data.content[:50]}...")
        try:
            metadata = input_data.metadata or {}
            
            doc_id = self._memory_agent.add_memory({
                "content": input_data.content,
                "source": input_data.source,
                "metadata": metadata
            })
            
            return {
                "success": True,
                "id": doc_id,
                "message": "Memory stored successfully"
            }
        except Exception as e:
            logger.error(f"Memory store error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to store memory"
            }
            
    # Define the task methods
    search_task = search
    store_task = store 