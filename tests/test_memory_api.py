import os
import sys
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Only try importing if app is importable
try:
    # Import API and models
    from app.web.app import app
    from app.agent.memory import MemoryAgent, MemoryItem
except ImportError:
    # Mock these for testing
    app = MagicMock()
    MemoryAgent = MagicMock()
    MemoryItem = MagicMock()


@pytest.mark.api
class TestMemoryAPI:
    """Tests for the memory API endpoints."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Skip if app is mocked (not importable)
        if isinstance(app, MagicMock):
            pytest.skip("App not importable, skipping test")
            
        # Create a mock memory agent
        self.mock_memory_agent = MagicMock()
        
        # Create fake response for query_memory
        self.mock_memory_agent.query_memory.return_value = [
            {"_id": "id1", "_score": 0.95, "content": "Test result 1"},
            {"_id": "id2", "_score": 0.85, "content": "Test result 2"}
        ]
        
        # Create fake response for add_memory
        self.mock_memory_agent.add_memory.return_value = "new_memory_id"
        
        # Add host and index_name attributes needed by the status endpoint
        self.mock_memory_agent.host = "http://test-host:8882"
        self.mock_memory_agent.index_name = "test_memory_index"
        
        # Ensure app has state attribute
        if not hasattr(app, 'state'):
            app.state = MagicMock()
        
        # Set memory_agent in app state directly
        app.state.memory_agent = self.mock_memory_agent
        
        # Create test client
        self.client = TestClient(app)
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clean up app state if needed
        if hasattr(app, 'state') and hasattr(app.state, 'memory_agent'):
            delattr(app.state, 'memory_agent')
    
    def test_query_memory_endpoint(self):
        """Test the query memory endpoint."""
        # Make request to query memory endpoint
        response = self.client.post(
            "/api/memory/query",
            json={"query": "test query", "limit": 2}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Check response data
        assert "results" in data
        assert len(data["results"]) == 2
        assert data["results"][0]["_id"] == "id1"
        assert data["results"][1]["_id"] == "id2"
        
        # Verify query_memory was called with correct parameters
        self.mock_memory_agent.query_memory.assert_called_once_with(
            "test query", limit=2)
    
    def test_add_memory_endpoint(self):
        """Test the add memory endpoint."""
        # Make request to add memory endpoint
        response = self.client.post(
            "/api/memory/add",
            json={
                "content": "Test memory content",
                "source": "api_test",
                "metadata": {"test_key": "test_value"}
            }
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Check response data
        assert data["success"] is True
        assert data["id"] == "new_memory_id"
        
        # Verify add_memory was called with correct parameters
        self.mock_memory_agent.add_memory.assert_called_once()
        call_arg = self.mock_memory_agent.add_memory.call_args[0][0]
        assert call_arg["content"] == "Test memory content"
        assert call_arg["source"] == "api_test"
        assert call_arg["metadata"] == {"test_key": "test_value"}
    
    def test_memory_status_endpoint(self):
        """Test the memory status endpoint."""
        # Make request to status endpoint
        response = self.client.get("/api/memory/status")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Check response data
        assert data["status"] == "available"
        assert data["host"] == "http://test-host:8882"
        assert data["index"] == "test_memory_index"
    
    def test_query_memory_endpoint_error(self):
        """Test error handling in query memory endpoint."""
        # Setup mock to raise an exception
        self.mock_memory_agent.query_memory.side_effect = Exception("Query failed")
        
        # Make request to query memory endpoint
        response = self.client.post(
            "/api/memory/query",
            json={"query": "error query"}
        )
        
        # Verify response
        assert response.status_code == 500
        data = response.json()
        
        # Check error message
        assert "error" in data
        assert "Query failed" in data["error"]
    
    def test_add_memory_endpoint_error(self):
        """Test error handling in add memory endpoint."""
        # Setup mock to raise an exception
        self.mock_memory_agent.add_memory.side_effect = Exception("Add failed")
        
        # Make request to add memory endpoint
        response = self.client.post(
            "/api/memory/add",
            json={
                "content": "Test memory that fails",
                "source": "api_test"
            }
        )
        
        # Verify response
        assert response.status_code == 500
        data = response.json()
        
        # Check error message
        assert "error" in data
        assert "Add failed" in data["error"]
    
    def test_no_memory_agent_available(self):
        """Test behavior when memory agent is not available."""
        # Remove memory_agent from app state
        if hasattr(app.state, 'memory_agent'):
            delattr(app.state, 'memory_agent')
            
        # Make request to status endpoint
        response = self.client.get("/api/memory/status")
            
        # Verify response indicates memory agent is not available
        assert response.status_code == 503


if __name__ == "__main__":
    pytest.main(["-v", "test_memory_api.py"]) 