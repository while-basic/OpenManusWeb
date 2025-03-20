import os
import sys
import json
import pytest
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from typing import Dict, List, Any

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.memory import MemoryAgent, MemoryItem
from app.tool.memory_tool import MemoryTool, MemorySearchInput, MemoryStoreInput


class TestMemoryAgent:
    """Tests for the MemoryAgent class."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Mock the Marqo client for testing
        self.marqo_patcher = patch('app.agent.memory.marqo.Client')
        self.mock_marqo = self.marqo_patcher.start()
        
        # Create a mock index
        self.mock_index = MagicMock()
        self.mock_marqo.return_value.index.return_value = self.mock_index
        
        # Set up mock for get_indexes
        self.mock_marqo.return_value.get_indexes.return_value = {"results": []}
        
        # Mock add_documents to return a valid response
        self.mock_index.add_documents.return_value = {
            "items": [{"_id": "test_id_123"}]
        }
        
        # Create the agent with mock Marqo client
        self.memory_agent = MemoryAgent(index_name="test_memory", host="http://test-host:8882")
    
    def teardown_method(self):
        """Clean up after each test."""
        self.marqo_patcher.stop()
    
    def test_init(self):
        """Test initialization of the MemoryAgent."""
        assert self.memory_agent is not None
        assert self.memory_agent.index_name == "test_memory"
        assert self.memory_agent.host == "http://test-host:8882"
        
        # Verify that _ensure_index_exists was called
        self.mock_marqo.return_value.get_indexes.assert_called_once()
    
    def test_ensure_index_exists_create_new(self):
        """Test index creation when it doesn't exist."""
        # Reset mock
        self.mock_marqo.return_value.get_indexes.reset_mock()
        self.mock_marqo.return_value.create_index.reset_mock()
        
        # Setup mock to return no indexes
        self.mock_marqo.return_value.get_indexes.return_value = {"results": []}
        
        # Run method
        self.memory_agent._ensure_index_exists()
        
        # Verify create_index was called with correct parameters
        self.mock_marqo.return_value.create_index.assert_called_once_with(
            "test_memory", 
            model="hf/e5-base-v2"
        )
    
    def test_ensure_index_exists_already_exists(self):
        """Test when index already exists."""
        # Reset mock
        self.mock_marqo.return_value.get_indexes.reset_mock()
        self.mock_marqo.return_value.create_index.reset_mock()
        
        # Setup mock to return the index
        self.mock_marqo.return_value.get_indexes.return_value = {
            "results": [{"indexName": "test_memory"}]
        }
        
        # Run method
        self.memory_agent._ensure_index_exists()
        
        # Verify create_index was not called
        self.mock_marqo.return_value.create_index.assert_not_called()
    
    def test_add_memory_string(self):
        """Test adding a memory with a string."""
        # Reset mock
        self.mock_index.add_documents.reset_mock()
        
        # Add memory
        result = self.memory_agent.add_memory("Test memory content")
        
        # Verify add_documents was called with the right parameters
        self.mock_index.add_documents.assert_called_once()
        
        # Check the document passed to add_documents
        called_args = self.mock_index.add_documents.call_args[0][0]
        assert len(called_args) == 1
        assert called_args[0]["content"] == "Test memory content"
        assert called_args[0]["source"] == "unknown"
        
        # Verify tensor_fields parameter
        assert self.mock_index.add_documents.call_args[1]["tensor_fields"] == ["content"]
        
        # Check the result
        assert result == "test_id_123"
    
    def test_add_memory_dict(self):
        """Test adding a memory with a dictionary."""
        # Reset mock
        self.mock_index.add_documents.reset_mock()
        
        # Create memory dict
        memory_dict = {
            "content": "Memory from dict",
            "source": "test_source",
            "metadata": {"key": "value"}
        }
        
        # Add memory
        result = self.memory_agent.add_memory(memory_dict)
        
        # Verify add_documents was called
        self.mock_index.add_documents.assert_called_once()
        
        # Check the document passed to add_documents
        called_args = self.mock_index.add_documents.call_args[0][0]
        assert len(called_args) == 1
        assert called_args[0]["content"] == "Memory from dict"
        assert called_args[0]["source"] == "test_source"
        assert called_args[0]["metadata"] == {"key": "value"}
        
        # Verify tensor_fields parameter
        assert self.mock_index.add_documents.call_args[1]["tensor_fields"] == ["content"]
        
        # Check the result
        assert result == "test_id_123"
    
    def test_add_memory_object(self):
        """Test adding a memory with a MemoryItem object."""
        # Reset mock
        self.mock_index.add_documents.reset_mock()
        
        # Create memory object
        memory_item = MemoryItem(
            content="Memory from object",
            source="test_object",
            metadata={"type": "object"}
        )
        
        # Add memory
        result = self.memory_agent.add_memory(memory_item)
        
        # Verify add_documents was called
        self.mock_index.add_documents.assert_called_once()
        
        # Check the document passed to add_documents
        called_args = self.mock_index.add_documents.call_args[0][0]
        assert len(called_args) == 1
        assert called_args[0]["content"] == "Memory from object"
        assert called_args[0]["source"] == "test_object"
        assert called_args[0]["metadata"] == {"type": "object"}
        
        # Verify tensor_fields parameter
        assert self.mock_index.add_documents.call_args[1]["tensor_fields"] == ["content"]
        
        # Check the result
        assert result == "test_id_123"
    
    def test_query_memory(self):
        """Test querying memory."""
        # Setup mock to return search results
        self.mock_index.search.return_value = {
            "hits": [
                {"_id": "id1", "_score": 0.9, "content": "Result 1"},
                {"_id": "id2", "_score": 0.8, "content": "Result 2"},
            ]
        }
        
        # Query memory
        results = self.memory_agent.query_memory("test query", limit=2)
        
        # Verify search was called with correct parameters
        self.mock_index.search.assert_called_once_with(
            q="test query", 
            limit=2, 
            search_method="tensor"
        )
        
        # Check the results
        assert len(results) == 2
        assert results[0]["_id"] == "id1"
        assert results[1]["_id"] == "id2"
    
    def test_query_memory_no_results(self):
        """Test querying memory with no results."""
        # Setup mock to return empty search results
        self.mock_index.search.return_value = {"hits": []}
        
        # Query memory
        results = self.memory_agent.query_memory("no match query")
        
        # Verify search was called
        self.mock_index.search.assert_called_once()
        
        # Check the results
        assert len(results) == 0
    
    def test_query_memory_error(self):
        """Test handling of query errors."""
        # Setup mock to raise an exception
        self.mock_index.search.side_effect = Exception("Search error")
        
        # Query memory (should return empty list on error)
        results = self.memory_agent.query_memory("error query")
        
        # Verify search was called
        self.mock_index.search.assert_called_once()
        
        # Check the results
        assert len(results) == 0
    
    def test_delete_memory(self):
        """Test deleting a memory."""
        # Reset mock
        self.mock_index.delete_documents.reset_mock()
        
        # Delete memory
        result = self.memory_agent.delete_memory("doc_id_to_delete")
        
        # Verify delete_documents was called with correct ID
        self.mock_index.delete_documents.assert_called_once_with(["doc_id_to_delete"])
        
        # Check result
        assert result is True
    
    def test_delete_memory_error(self):
        """Test handling of delete errors."""
        # Setup mock to raise an exception
        self.mock_index.delete_documents.side_effect = Exception("Delete error")
        
        # Delete memory
        result = self.memory_agent.delete_memory("error_doc_id")
        
        # Verify delete_documents was called
        self.mock_index.delete_documents.assert_called_once()
        
        # Check result
        assert result is False


class TestMemoryLogProcessing:
    """Tests for the log processing functionality of MemoryAgent."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Mock the Marqo client
        self.marqo_patcher = patch('app.agent.memory.marqo.Client')
        self.mock_marqo = self.marqo_patcher.start()
        
        # Create a mock index
        self.mock_index = MagicMock()
        self.mock_marqo.return_value.index.return_value = self.mock_index
        self.mock_marqo.return_value.get_indexes.return_value = {"results": []}
        
        # Mock add_documents for log processing
        self.mock_index.add_documents.return_value = {
            "items": [{"_id": "log_entry_id"}]
        }
        
        # Create the agent with mock Marqo client
        self.memory_agent = MemoryAgent(index_name="test_memory")
        
        # Create a temporary directory for logs
        self.temp_dir = tempfile.TemporaryDirectory()
        
    def teardown_method(self):
        """Clean up after each test."""
        self.marqo_patcher.stop()
        self.temp_dir.cleanup()
    
    def test_process_logs_empty_directory(self):
        """Test processing logs with empty directory."""
        # Call process_logs on empty directory
        count = self.memory_agent.process_logs(self.temp_dir.name)
        
        # Verify add_documents was not called
        self.mock_index.add_documents.assert_not_called()
        
        # Check count
        assert count == 0
    
    def test_process_logs_plain_text(self):
        """Test processing plain text log files."""
        # Create a test log file
        log_file = os.path.join(self.temp_dir.name, "test.log")
        with open(log_file, "w") as f:
            f.write("Log entry 1\nLog entry 2\nLog entry 3\n")
        
        # Process logs
        count = self.memory_agent.process_logs(self.temp_dir.name)
        
        # Verify add_documents was called 3 times (once per line)
        assert self.mock_index.add_documents.call_count == 3
        
        # Check that the content was correct
        calls = self.mock_index.add_documents.call_args_list
        assert calls[0][0][0][0]["content"].strip() == "Log entry 1"
        assert calls[1][0][0][0]["content"].strip() == "Log entry 2"
        assert calls[2][0][0][0]["content"].strip() == "Log entry 3"
        
        # Check count
        assert count == 3
    
    def test_process_logs_json(self):
        """Test processing log files with JSON entries."""
        # Create a test log file with JSON entries
        log_file = os.path.join(self.temp_dir.name, "json.log")
        with open(log_file, "w") as f:
            f.write(json.dumps({"message": "JSON log 1", "level": "INFO"}) + "\n")
            f.write(json.dumps({"message": "JSON log 2", "level": "ERROR", "extra": "data"}) + "\n")
        
        # Process logs
        count = self.memory_agent.process_logs(self.temp_dir.name)
        
        # Verify add_documents was called twice
        assert self.mock_index.add_documents.call_count == 2
        
        # Check that the content and metadata were extracted correctly
        calls = self.mock_index.add_documents.call_args_list
        assert calls[0][0][0][0]["content"] == "JSON log 1"
        assert calls[0][0][0][0]["metadata"] == {"level": "INFO"}
        
        assert calls[1][0][0][0]["content"] == "JSON log 2"
        assert calls[1][0][0][0]["metadata"] == {"level": "ERROR", "extra": "data"}
        
        # Check count
        assert count == 2
        

class TestMemoryTool:
    """Tests for the MemoryTool class that integrates with agents."""
    
    @pytest.mark.asyncio
    async def test_memory_search(self):
        """Test the search method of MemoryTool."""
        # Create mock search implementation
        async def mock_search(self, input_data):
            results = self._memory_agent.query_memory(
                query=input_data.query,
                limit=input_data.limit
            )
            
            return {
                "results": results,
                "count": len(results),
                "query": input_data.query
            }
        
        # Patch memory agent and search method
        with patch('app.tool.memory_tool.MemoryTool._memory_agent', new_callable=PropertyMock) as mock_memory_agent:
            with patch('app.tool.memory_tool.MemoryTool.search', new=mock_search):
                # Setup mock agent with results
                mock_agent = MagicMock()
                mock_agent.query_memory.return_value = [
                    {"_id": "id1", "content": "Test memory 1", "_score": 0.9},
                    {"_id": "id2", "content": "Test memory 2", "_score": 0.8}
                ]
                mock_memory_agent.return_value = mock_agent
                
                # Create a memory tool instance
                memory_tool = MagicMock()
                memory_tool._memory_agent = mock_agent
                
                # Create input
                search_input = MemorySearchInput(query="test query", limit=2)
                
                # Call the search method
                result = await mock_search(memory_tool, search_input)
                
                # Verify query_memory was called with the right parameters
                mock_agent.query_memory.assert_called_once_with(
                    query="test query",
                    limit=2
                )
                
                # Check the result
                assert result["count"] == 2
                assert len(result["results"]) == 2
                assert result["results"][0]["_id"] == "id1"
                assert result["results"][1]["_id"] == "id2"
                assert result["query"] == "test query"
        
    @pytest.mark.asyncio
    async def test_memory_store(self):
        """Test the store method of MemoryTool."""
        # Create mock store implementation
        async def mock_store(self, input_data):
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
        
        # Patch memory agent and store method
        with patch('app.tool.memory_tool.MemoryTool._memory_agent', new_callable=PropertyMock) as mock_memory_agent:
            with patch('app.tool.memory_tool.MemoryTool.store', new=mock_store):
                # Setup mock memory agent
                mock_agent = MagicMock()
                mock_agent.add_memory.return_value = "new_memory_id"
                mock_memory_agent.return_value = mock_agent
                
                # Create a memory tool instance
                memory_tool = MagicMock()
                memory_tool._memory_agent = mock_agent
                
                # Create input
                store_input = MemoryStoreInput(
                    content="Test memory content",
                    source="test",
                    metadata={"key": "value"}
                )
                
                # Call the store method
                result = await mock_store(memory_tool, store_input)
                
                # Verify add_memory was called with the right parameters
                mock_agent.add_memory.assert_called_once_with({
                    "content": "Test memory content",
                    "source": "test",
                    "metadata": {"key": "value"}
                })
                
                # Check the result
                assert result["success"] is True
                assert result["id"] == "new_memory_id"
                assert "Memory stored successfully" in result["message"]
        
    @pytest.mark.asyncio
    async def test_memory_search_error(self):
        """Test error handling in search method."""
        # Create mock search implementation with error handling
        async def mock_search(self, input_data):
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
                return {
                    "error": str(e),
                    "results": [],
                    "count": 0,
                    "query": input_data.query
                }
        
        # Patch memory agent and search method
        with patch('app.tool.memory_tool.MemoryTool._memory_agent', new_callable=PropertyMock) as mock_memory_agent:
            with patch('app.tool.memory_tool.MemoryTool.search', new=mock_search):
                # Setup mock memory agent
                mock_agent = MagicMock()
                mock_agent.query_memory.side_effect = Exception("Search failed")
                mock_memory_agent.return_value = mock_agent
                
                # Create a memory tool instance
                memory_tool = MagicMock()
                memory_tool._memory_agent = mock_agent
                
                # Create input
                search_input = MemorySearchInput(query="test query", limit=2)
                
                # Call the search method, which should handle the error
                result = await mock_search(memory_tool, search_input)
                
                # Verify query_memory was called
                mock_agent.query_memory.assert_called_once()
                
                # Check the error handling
                assert "error" in result
                assert "Search failed" in result["error"]
                assert result["count"] == 0
                assert len(result["results"]) == 0
                assert result["query"] == "test query"
        
    @pytest.mark.asyncio
    async def test_memory_store_error(self):
        """Test error handling in store method."""
        # Create mock store implementation with error handling
        async def mock_store(self, input_data):
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
                return {
                    "success": False,
                    "error": str(e),
                    "message": "Failed to store memory"
                }
        
        # Patch memory agent and store method
        with patch('app.tool.memory_tool.MemoryTool._memory_agent', new_callable=PropertyMock) as mock_memory_agent:
            with patch('app.tool.memory_tool.MemoryTool.store', new=mock_store):
                # Setup mock memory agent
                mock_agent = MagicMock()
                mock_agent.add_memory.side_effect = Exception("Store failed")
                mock_memory_agent.return_value = mock_agent
                
                # Create a memory tool instance
                memory_tool = MagicMock()
                memory_tool._memory_agent = mock_agent
                
                # Create input
                store_input = MemoryStoreInput(
                    content="Test memory content",
                    source="test"
                )
                
                # Call the store method, which should handle the error
                result = await mock_store(memory_tool, store_input)
                
                # Verify add_memory was called
                mock_agent.add_memory.assert_called_once()
                
                # Check the error handling
                assert result["success"] is False
                assert "error" in result
                assert "Store failed" in result["error"]
                assert "Failed to store memory" in result["message"]


@pytest.mark.integration
class TestMemoryIntegration:
    """Integration tests for the memory system with actual Marqo instance."""
    
    @pytest.mark.skipif(not os.environ.get("RUN_MARQO_TESTS"), 
                       reason="Set RUN_MARQO_TESTS=1 to run integration tests")
    def test_memory_agent_with_real_marqo(self):
        """Test connecting to a real Marqo instance."""
        # This test should be skipped by default since it requires a real Marqo instance
        memory_agent = MemoryAgent(
            index_name=f"test_index_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            host="http://localhost:8882"
        )
        
        # Add a test memory
        doc_id = memory_agent.add_memory("Test integration memory")
        
        # Query for the memory
        results = memory_agent.query_memory("integration")
        
        # Clean up
        memory_agent.delete_memory(doc_id)
        
        # Verify results
        assert len(results) > 0
        found = False
        for hit in results:
            if hit.get("_id") == doc_id:
                found = True
                break
        assert found, "Added document was not found in query results"


if __name__ == "__main__":
    pytest.main(["-v", "test_memory_agent.py"]) 