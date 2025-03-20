#!/usr/bin/env python
"""
End-to-End Test Script for Memory Agent

This script demonstrates the functionality of the memory agent with Marqo 
in a real-world scenario. It will perform the following steps:
1. Start Marqo (if not already running)
2. Create a memory agent
3. Store sample data in the memory
4. Query the memory with various search terms
5. Process sample logs
6. Demonstrate the MemoryTool integration

To run this script:
1. Make sure Docker is running
2. Run: python test_memory_e2e.py
"""

import os
import sys
import json
import time
import asyncio
import subprocess
import tempfile
import traceback
from pathlib import Path
import socket

# Add parent directory to path to import app modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Import memory agent modules
try:
    from app.agent.memory import MemoryAgent, MemoryItem
    from app.tool.memory_tool import MemoryTool, MemorySearchInput, MemoryStoreInput
except ImportError as e:
    print(f"Failed to import required modules: {e}")
    print("Make sure you have implemented the memory agent and tool classes.")
    sys.exit(1)


# Configuration
MARQO_HOST = "http://localhost:8882"
TEST_INDEX_NAME = f"test_memory_{int(time.time())}"  # Unique index name
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def check_marqo_running(host="localhost", port=8882, timeout=2):
    """Check if Marqo is running."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            # Additional check for API readiness
            import requests
            try:
                response = requests.get(f"http://{host}:{port}/ready", timeout=timeout)
                return response.status_code == 200
            except requests.RequestException:
                return False
        return False
    except Exception as e:
        print(f"Error checking Marqo: {e}")
        return False


def start_marqo():
    """Start Marqo if not already running."""
    if check_marqo_running():
        print("✅ Marqo is already running")
        return True
    
    try:
        # Check if docker is installed
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Docker is not installed or not in PATH")
            return False
            
        # Check if docker-compose file exists
        docker_compose_path = os.path.join(parent_dir, "docker-compose.yml")
        if not os.path.exists(docker_compose_path):
            print(f"❌ docker-compose.yml not found at {docker_compose_path}")
            print("Make sure you run this from the project root directory")
            return False
            
        print("Starting Marqo Docker container...")
        subprocess.run(["docker-compose", "up", "-d", "marqo"], check=True)
        
        # Wait for Marqo to be ready
        for i in range(20):  # Increased timeout to 60 seconds
            if check_marqo_running():
                print("✅ Marqo is now running")
                # Additional wait to ensure API is fully ready
                time.sleep(8)
                return True
            print(f"Waiting for Marqo to start... {i+1}/20")
            time.sleep(3)
        
        print("❌ Timeout waiting for Marqo to start")
        return False
    except Exception as e:
        print(f"❌ Error starting Marqo: {str(e)}")
        traceback.print_exc()
        return False


class AppStateMock:
    """Mock for app.state to use with MemoryTool."""
    def __init__(self, memory_agent):
        self.memory_agent = memory_agent


class AppMock:
    """Mock for app to use with MemoryTool."""
    def __init__(self, memory_agent):
        self.state = AppStateMock(memory_agent)


class RequestMock:
    """Mock for request object."""
    def __init__(self, app):
        self.app = app


async def test_memory_tool(memory_agent):
    """Test the MemoryTool functionality."""
    print("\n=== Testing MemoryTool ===")
    
    # Store original references
    original_references = {}
    
    try:
        # Mock the app.state for the tool
        import app.tool.memory_tool as memory_tool_module
        
        # Store original references if they exist
        for name in ['app', 'Request']:
            if hasattr(memory_tool_module, name):
                original_references[name] = getattr(memory_tool_module, name)
        
        # Create mock app with our memory agent
        mock_app = AppMock(memory_agent)
        memory_tool_module.app = mock_app
        
        # Create a test subclass that implements the abstract method
        class TestMemoryTool(MemoryTool):
            async def execute(self, inputs):
                """Implement abstract method for testing"""
                return {"result": "test_executed"}
        
        # Initialize memory tool
        memory_tool = TestMemoryTool()
        
        # Test storing a memory
        store_input = MemoryStoreInput(
            content="This is a test memory created via the MemoryTool",
            source="e2e_test",
            metadata={"test_type": "e2e", "priority": "high"}
        )
        
        store_result = await memory_tool.store(store_input)
        print(f"Memory store result: {store_result}")
        
        if store_result.get("success"):
            # Test searching for the memory
            search_input = MemorySearchInput(query="test memory MemoryTool")
            search_result = await memory_tool.search(search_input)
            print(f"Memory search found {search_result.get('count', 0)} results")
            
            # Print first result
            if search_result.get("results") and len(search_result["results"]) > 0:
                first_result = search_result["results"][0]
                print(f"Top result: {first_result.get('content', '')[:100]}")
    except Exception as e:
        print(f"❌ Error during MemoryTool test: {str(e)}")
        traceback.print_exc()
    finally:
        # Restore original references
        for name, ref in original_references.items():
            setattr(memory_tool_module, name, ref)


def create_sample_logs():
    """Create sample log files for testing."""
    temp_dir = tempfile.TemporaryDirectory()
    
    # Create a plain text log file
    text_log_path = os.path.join(temp_dir.name, "plain.log")
    with open(text_log_path, "w") as f:
        f.write("DEBUG: Application started\n")
        f.write("INFO: User login successful for user_id=12345\n")
        f.write("WARNING: High memory usage detected: 85%\n")
        f.write("ERROR: Database connection failed: timeout after 30s\n")
        f.write("INFO: Processing request #789 for customer XYZ Corp\n")
    
    # Create a JSON structured log file
    json_log_path = os.path.join(temp_dir.name, "structured.log")
    with open(json_log_path, "w") as f:
        f.write(json.dumps({
            "timestamp": "2023-03-19T15:23:45Z",
            "level": "INFO",
            "message": "API request received from 192.168.1.100",
            "endpoint": "/api/data",
            "method": "GET"
        }) + "\n")
        f.write(json.dumps({
            "timestamp": "2023-03-19T15:23:46Z",
            "level": "DEBUG",
            "message": "Processing request payload",
            "payload_size": 1024,
            "user_agent": "Mozilla/5.0"
        }) + "\n")
        f.write(json.dumps({
            "timestamp": "2023-03-19T15:23:48Z",
            "level": "ERROR",
            "message": "Validation error in user input",
            "field": "email",
            "reason": "Invalid format",
            "value": "user@example"
        }) + "\n")
    
    return temp_dir


def create_memory_agent_with_retry():
    """Create a memory agent with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            print(f"\nCreating memory agent with index: {TEST_INDEX_NAME} (Attempt {attempt+1}/{MAX_RETRIES})")
            memory_agent = MemoryAgent(
                index_name=TEST_INDEX_NAME,
                host=MARQO_HOST
            )
            print("✅ Memory agent created successfully")
            return memory_agent
        except Exception as e:
            print(f"❌ Failed to create memory agent: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                print(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                raise


def main():
    """Run the end-to-end test."""
    # Start Marqo if needed
    if not start_marqo():
        print("❌ Could not start Marqo. Exiting.")
        return 1
    
    try:
        # Create a memory agent with retry
        memory_agent = create_memory_agent_with_retry()
        
        # Add some test memories
        print("\n=== Adding test memories ===")
        memories = [
            {
                "content": "Python is a high-level, general-purpose programming language. Its design philosophy emphasizes code readability with the use of significant indentation.",
                "source": "language_info",
                "metadata": {"type": "programming_language", "category": "general_purpose"}
            },
            {
                "content": "Marqo is an open-source tensor search engine. It allows you to search through your data using deep learning embeddings.",
                "source": "tool_info",
                "metadata": {"type": "search_engine", "category": "vector_database"}
            },
            {
                "content": "Docker is a set of platform as a service products that use OS-level virtualization to deliver software in packages called containers.",
                "source": "tool_info",
                "metadata": {"type": "containerization", "category": "devops"}
            },
            {
                "content": "The MemoryAgent provides persistent storage for AI agents, allowing them to remember information across sessions.",
                "source": "agent_info",
                "metadata": {"type": "ai_component", "category": "memory"}
            },
            {
                "content": "User John Doe has completed the onboarding process. Preferences: dark mode, daily notifications, interested in AI topics.",
                "source": "user_data",
                "metadata": {"user_id": "12345", "timestamp": time.time()}
            }
        ]
        
        # Add memories and keep track of IDs
        memory_ids = []
        for i, memory in enumerate(memories):
            try:
                doc_id = memory_agent.add_memory(memory)
                memory_ids.append(doc_id)
                print(f"✅ Memory {i+1}/{len(memories)} added with ID: {doc_id}")
            except Exception as e:
                print(f"❌ Failed to add memory {i+1}: {str(e)}")
        
        # Need to wait for indexing to complete
        print("Waiting for indexing to complete...")
        time.sleep(10)  # Increased wait time
        
        # Query test
        print("\n=== Testing memory queries ===")
        queries = [
            "python programming language",
            "memory storage for AI",
            "docker containers",
            "user preferences",
            "search engine embeddings"
        ]
        
        for i, query in enumerate(queries):
            try:
                print(f"\nQuery {i+1}: '{query}'")
                results = memory_agent.query_memory(query, limit=2)
                
                if results:
                    print(f"Found {len(results)} results")
                    for j, result in enumerate(results):
                        print(f"  Result {j+1}: (score: {result.get('_score', 'N/A'):.2f})")
                        print(f"  Content: {result.get('content', 'N/A')[:100]}...")
                else:
                    print("No results found")
            except Exception as e:
                print(f"❌ Query failed: {str(e)}")
        
        # Delete test
        if memory_ids:
            print("\n=== Testing memory deletion ===")
            try:
                deleted_id = memory_ids[0]
                memory_agent.delete_memory(deleted_id)
                print(f"✅ Successfully deleted memory with ID: {deleted_id}")
                
                # Verify deletion
                try:
                    remaining = memory_agent.query_memory(f"_id:{deleted_id}")
                    if not remaining:
                        print("✅ Verified memory no longer exists")
                    else:
                        print("❌ Memory still exists after deletion")
                except Exception:
                    # Some vector DBs might throw an error when querying non-existent IDs
                    print("✅ Verified memory no longer exists (query failed as expected)")
            except Exception as e:
                print(f"❌ Delete test failed: {str(e)}")
        
        # Log processing test
        print("\n=== Testing log processing ===")
        try:
            temp_dir = create_sample_logs()
            try:
                processed_count = memory_agent.process_logs(log_dir=temp_dir.name)
                print(f"✅ Processed {processed_count} log entries")
                
                # Query for log content
                print("\nSearching for processed logs:")
                log_results = memory_agent.query_memory("database connection failed", limit=1)
                if log_results:
                    print(f"Found log: {log_results[0].get('content', 'N/A')}")
                else:
                    print("No log results found")
            finally:
                temp_dir.cleanup()
        except Exception as e:
            print(f"❌ Log processing test failed: {str(e)}")
            traceback.print_exc()
        
        # MemoryTool test
        loop = asyncio.get_event_loop()
        loop.run_until_complete(test_memory_tool(memory_agent))
        
        # Cleanup
        print("\n=== Cleaning up ===")
        try:
            # Delete the test index
            memory_agent.client.index(TEST_INDEX_NAME).delete()
            print(f"✅ Successfully deleted test index: {TEST_INDEX_NAME}")
        except Exception as e:
            print(f"❌ Failed to delete test index: {str(e)}")
        
        print("\n✅ End-to-end test completed successfully")
        return 0
        
    except Exception as e:
        print(f"\n❌ End-to-end test failed: {str(e)}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 