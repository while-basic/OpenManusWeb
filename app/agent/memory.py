import os
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import marqo
from loguru import logger
from pydantic import BaseModel, Field


class MemoryItem(BaseModel):
    """A single memory item to be stored in the vector database."""
    content: str = Field(..., description="The content of the memory")
    source: str = Field(..., description="Source of the memory (e.g., 'logs', 'user_input')")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class MemoryAgent:
    """Agent that handles memory operations with Marqo vector database."""
    
    def __init__(self, index_name: str = "sith_memory", host: str = "http://localhost:8882"):
        """Initialize the memory agent with connection to Marqo.
        
        Args:
            index_name: Name of the index to use in Marqo
            host: Host address for the Marqo instance
        """
        self.index_name = index_name
        self.host = host
        self.client = marqo.Client(url=host)
        self._ensure_index_exists()
        logger.info(f"Memory agent initialized with Marqo at {host}, index: {index_name}")
        
    def _ensure_index_exists(self):
        """Ensure the required index exists in Marqo."""
        try:
            indexes = self.client.get_indexes()
            if self.index_name not in [index["indexName"] for index in indexes.get("results", [])]:
                logger.info(f"Creating Marqo index: {self.index_name}")
                self.client.create_index(
                    self.index_name,
                    model="hf/e5-base-v2"  # Using a standard text embedding model
                )
            logger.debug(f"Marqo index {self.index_name} exists")
        except Exception as e:
            logger.error(f"Error checking/creating Marqo index: {e}")
            raise
            
    def add_memory(self, item: Union[MemoryItem, Dict[str, Any], str]) -> str:
        """Add a memory item to the vector database.
        
        Args:
            item: Memory item to add (MemoryItem, dict, or string content)
        
        Returns:
            id: The ID of the added document
        """
        try:
            if isinstance(item, str):
                memory_item = MemoryItem(content=item, source="unknown")
            elif isinstance(item, dict):
                memory_item = MemoryItem(**item)
            else:
                memory_item = item
                
            document = memory_item.model_dump()
            result = self.client.index(self.index_name).add_documents(
                [document], 
                tensor_fields=["content"]  # Vectorize the content field
            )
            doc_id = result["items"][0]["_id"]
            logger.debug(f"Added memory with ID {doc_id}: {memory_item.content[:50]}...")
            return doc_id
        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            raise
    
    def query_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Query the vector database for relevant memories.
        
        Args:
            query: The query string
            limit: Maximum number of results to return
            
        Returns:
            List of matching memory items with similarity scores
        """
        try:
            results = self.client.index(self.index_name).search(
                q=query,
                limit=limit,
                search_method="tensor"
            )
            logger.debug(f"Query '{query}' returned {len(results.get('hits', []))} results")
            return results.get("hits", [])
        except Exception as e:
            logger.error(f"Error querying memory: {e}")
            return []
            
    def delete_memory(self, doc_id: str) -> bool:
        """Delete a memory item from the vector database.
        
        Args:
            doc_id: The ID of the document to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.client.index(self.index_name).delete_documents([doc_id])
            logger.debug(f"Deleted memory with ID {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting memory: {e}")
            return False
            
    def process_logs(self, log_directory: str = "logs") -> int:
        """Process log files and extract information to store in memory.
        
        Args:
            log_directory: Directory containing log files
            
        Returns:
            int: Number of memory items added
        """
        count = 0
        try:
            for filename in os.listdir(log_directory):
                if not filename.endswith(".log"):
                    continue
                    
                filepath = os.path.join(log_directory, filename)
                logger.info(f"Processing log file: {filepath}")
                
                with open(filepath, "r") as f:
                    for line in f:
                        try:
                            # Skip empty lines
                            if not line.strip():
                                continue
                                
                            # Try to parse as JSON if possible
                            try:
                                data = json.loads(line)
                                content = data.get("message", line)
                                metadata = {k: v for k, v in data.items() if k != "message"}
                            except json.JSONDecodeError:
                                content = line
                                metadata = {}
                                
                            # Store in memory
                            self.add_memory(MemoryItem(
                                content=content,
                                source=f"log:{filename}",
                                metadata=metadata
                            ))
                            count += 1
                        except Exception as e:
                            logger.error(f"Error processing log line: {e}")
                            
        except Exception as e:
            logger.error(f"Error processing logs: {e}")
            
        logger.info(f"Processed {count} memory items from logs")
        return count 