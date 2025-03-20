import os
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import marqo
from loguru import logger
from pydantic import BaseModel, Field
import uuid
import traceback


class MemoryItem(BaseModel):
    """A single memory item to be stored in the vector database."""
    content: str = Field(..., description="The content of the memory")
    source: str = Field(..., description="Source of the memory (e.g., 'logs', 'user_input')")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class MemoryAgent:
    """Agent for managing vectorized memories."""
    
    def __init__(self, index_name: str = "sith_memory", host: str = "http://localhost:8882"):
        """Initialize the memory agent.
        
        Args:
            index_name: Name of the index to use in the vector store.
            host: Host address of the Marqo server.
        """
        logger.info(f"Initializing MemoryAgent with index_name={index_name}, host={host}")
        try:
            self.client = marqo.Client(url=host)
            self.index_name = index_name
            
            # Check if index exists, create if not
            try:
                indexes = self.client.get_indexes()
                index_exists = any(index['indexName'] == index_name for index in indexes.get('results', []))
                
                if not index_exists:
                    logger.info(f"Creating new index '{index_name}'")
                    settings = {
                        "treat_urls_and_pointers_as_images": False,
                        "model": "sentence-transformers/all-MiniLM-L6-v2"
                    }
                    self.client.create_index(index_name, settings_dict=settings)
                    logger.info(f"Successfully created index '{index_name}'")
                else:
                    logger.info(f"Using existing index '{index_name}'")
            except Exception as e:
                logger.error(f"Error checking/creating index: {str(e)}")
                logger.error(traceback.format_exc())
                raise
                
        except Exception as e:
            logger.error(f"Failed to initialize MemoryAgent: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def add_memory(self, memory: Union[Dict[str, Any], MemoryItem]) -> str:
        """Add a memory to the vector store.
        
        Args:
            memory: Dictionary or MemoryItem containing memory data with 'content' key.
                   Can optionally include 'source' and 'metadata'.
        
        Returns:
            str: ID of the newly created memory document.
        """
        try:
            # Convert MemoryItem to dict if needed
            if isinstance(memory, MemoryItem):
                memory_dict = memory.model_dump()
            else:
                memory_dict = memory
                
            # Validate memory
            if not memory_dict.get('content'):
                raise ValueError("Memory must contain 'content'")
            
            # Generate a UUID for the document
            doc_id = str(uuid.uuid4())
            
            # Add timestamp if not present
            if 'timestamp' not in memory_dict:
                memory_dict['timestamp'] = datetime.now().isoformat()
                
            # Add defaults for source and metadata if not present
            if 'source' not in memory_dict:
                memory_dict['source'] = 'unknown'
            if 'metadata' not in memory_dict:
                memory_dict['metadata'] = {}
                
            # Ensure importance is numeric if present
            if 'importance' in memory_dict.get('metadata', {}) and isinstance(memory_dict['metadata']['importance'], str):
                try:
                    if memory_dict['metadata']['importance'].lower() == 'high':
                        memory_dict['metadata']['importance'] = 10
                    elif memory_dict['metadata']['importance'].lower() == 'medium':
                        memory_dict['metadata']['importance'] = 5
                    elif memory_dict['metadata']['importance'].lower() == 'low':
                        memory_dict['metadata']['importance'] = 1
                    else:
                        # Try to convert to int
                        memory_dict['metadata']['importance'] = int(memory_dict['metadata']['importance'])
                except (ValueError, AttributeError):
                    # Default to 5 if conversion fails
                    memory_dict['metadata']['importance'] = 5
            
            logger.info(f"Adding memory with ID {doc_id}, content length: {len(memory_dict['content'])}")
            logger.debug(f"Memory details: source={memory_dict['source']}, metadata={memory_dict['metadata']}")
            
            # Add document to index
            result = self.client.index(self.index_name).add_documents(
                [{"_id": doc_id, **memory_dict}],
                tensor_fields=["content"]
            )
            
            logger.info(f"Successfully added memory with ID {doc_id}")
            logger.debug(f"Add result: {result}")
            
            return doc_id
            
        except Exception as e:
            logger.error(f"Error adding memory: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def query_memory(self, query: str, limit: int = 10, filter_dict: Optional[Dict] = None) -> List[Dict]:
        """Query memories using semantic search.
        
        Args:
            query: The query text or "*" to retrieve recent items.
            limit: Maximum number of results to return.
            filter_dict: Optional filter to apply to the query.
            
        Returns:
            List of memory documents, ordered by relevance.
        """
        try:
            logger.info(f"Querying memory with query='{query}', limit={limit}")
            if filter_dict:
                logger.debug(f"Using filter: {filter_dict}")
            
            if query == "*":
                # For wildcard queries, return most recent memories
                results = self.client.index(self.index_name).search(
                    q=query,
                    limit=limit,
                    search_method=marqo.SearchMethods.LEXICAL
                )
            else:
                # Use semantic search for actual queries
                results = self.client.index(self.index_name).search(
                    q=query,
                    limit=limit
                )
            
            hits = results.get("hits", [])
            logger.info(f"Query returned {len(hits)} results")
            
            return hits
            
        except Exception as e:
            logger.error(f"Error querying memory: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def delete_memory(self, doc_id: str) -> bool:
        """Delete a memory by ID.
        
        Args:
            doc_id: ID of the memory to delete.
            
        Returns:
            bool: True if successfully deleted, False otherwise.
        """
        try:
            logger.info(f"Deleting memory with ID {doc_id}")
            
            result = self.client.index(self.index_name).delete_documents([doc_id])
            
            # Check if any documents were actually deleted
            if result.get('status') == 'ok' and result.get('deleted', 0) > 0:
                logger.info(f"Successfully deleted memory with ID {doc_id}")
                return True
            else:
                logger.warning(f"Memory with ID {doc_id} not found or could not be deleted")
                logger.debug(f"Delete result: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting memory: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def clear_all_memories(self) -> bool:
        """Delete all memories in the index. Use with caution!
        
        Returns:
            bool: True if successfully deleted, False otherwise.
        """
        try:
            logger.warning(f"Clearing all memories from index {self.index_name}")
            
            # Option 1: Delete index and recreate it
            self.client.delete_index(self.index_name)
            
            settings = {
                "treat_urls_and_pointers_as_images": False,
                "model": "sentence-transformers/all-MiniLM-L6-v2"
            }
            self.client.create_index(self.index_name, settings_dict=settings)
            
            logger.info(f"Successfully cleared all memories by recreating index {self.index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing memories: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def update_memory(self, doc_id: str, updates: Dict[str, Any]) -> bool:
        """Update specific fields of a memory.
        
        Args:
            doc_id: ID of the memory to update.
            updates: Dictionary of fields to update.
            
        Returns:
            bool: True if successfully updated, False otherwise.
        """
        try:
            logger.info(f"Updating memory with ID {doc_id}")
            logger.debug(f"Update fields: {updates}")
            
            # First get the existing document
            results = self.client.index(self.index_name).search(
                q="*",
                filter={"_id": doc_id},
                limit=1,
                search_method=marqo.SearchMethods.LEXICAL
            )
            
            hits = results.get("hits", [])
            if not hits:
                logger.warning(f"Memory with ID {doc_id} not found")
                return False
            
            # Get the existing document
            existing_doc = hits[0]
            
            # Create updated document by merging existing with updates
            updated_doc = {**existing_doc}
            for key, value in updates.items():
                # Special handling for metadata - merge rather than replace
                if key == "metadata" and "metadata" in existing_doc:
                    updated_doc["metadata"] = {**existing_doc["metadata"], **value}
                else:
                    updated_doc[key] = value
            
            # Remove marqo's internal fields
            for key in ['_id', '_score']:
                if key in updated_doc:
                    del updated_doc[key]
            
            # Update document
            result = self.client.index(self.index_name).add_documents(
                [{"_id": doc_id, **updated_doc}],
                tensor_fields=["content"]
            )
            
            logger.info(f"Successfully updated memory with ID {doc_id}")
            logger.debug(f"Update result: {result}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating memory: {str(e)}")
            logger.error(traceback.format_exc())
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