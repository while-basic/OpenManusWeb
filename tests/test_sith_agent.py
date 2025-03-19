import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.agent.sith import Sith
from app.schema import AgentState, Function, Message, ToolCall
from app.tool import ToolCollection

@pytest.fixture
def sith_response():
    """Fixture for Sith agent response."""
    return {
        "id": "sith-id",
        "choices": [
            {
                "message": {
                    "content": "Execute Order 66. All Jedi must be eliminated.",
                    "role": "assistant"
                },
                "index": 0,
                "finish_reason": "stop"
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
    }

@pytest.fixture
def tool_call_response():
    """Fixture for tool call response for Sith agent."""
    return {
        "id": "tool-call-id",
        "choices": [
            {
                "message": {
                    "content": None,
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "execute_order",
                                "arguments": json.dumps({"order_number": "66"})
                            }
                        }
                    ]
                },
                "index": 0,
                "finish_reason": "tool_calls"
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
    }

@pytest.mark.asyncio
class TestSithAgent:
    """Tests for the Sith agent."""

    @patch("app.llm.LLM.ask")
    async def test_sith_initialization(self, mock_ask):
        """Test that the Sith agent initializes correctly with default values."""
        # Initialize a Sith agent
        agent = Sith(model="gpt-4")
        
        # Check basic properties
        assert agent.name == "Sith"
        assert "versatile" in agent.description.lower()
        assert isinstance(agent.available_tools, ToolCollection)
        assert agent.model == "gpt-4"
        assert agent.state == AgentState.IDLE
        assert agent.current_step == 0
        
        # Verify tools are available
        tool_names = [tool.name for tool in agent.available_tools.tools]
        assert "python_execute" in tool_names
        assert "google_search" in tool_names
        assert "browser_use" in tool_names
        assert "file_saver" in tool_names
        assert "terminate" in tool_names

    @patch("app.llm.LLM.ask")
    async def test_sith_memory_management(self, mock_ask):
        """Test the Sith agent's memory management capabilities."""
        agent = Sith(model="gpt-4")
        
        # Add a message to the agent's memory
        test_message = Message.user_message("Test message")
        agent.memory.add_message(test_message)
        
        # Verify the message was added
        assert len(agent.memory.messages) == 1
        assert agent.memory.messages[0].content == "Test message"
        
        # Clear memory
        agent.memory.clear()
        assert len(agent.memory.messages) == 0

    @pytest.mark.asyncio
    @patch("app.llm.LLM.ask_tool")
    async def test_sith_basic_response(self, mock_ask_tool):
        """Test that the Sith agent can process a basic request without tool calls."""
        # Create mock response
        mock_response = MagicMock()
        mock_response.content = "Execute Order 66. All Jedi must be eliminated."
        mock_response.tool_calls = None
        mock_ask_tool.return_value = mock_response
        
        agent = Sith(model="gpt-4")
        agent.memory.add_message(Message.user_message("What is Order 66?"))
        
        # Simulate a step
        await agent.step()
        
        # Verify the agent processed the response correctly
        assert "Execute Order 66" in agent.messages[-1].content
        assert agent.messages[-1].role == "assistant"
        
        # Verify LLM was called with correct parameters
        mock_ask_tool.assert_called_once()
        # Verify system prompt was included in the call
        # Use a more general check since the prompt might change
        assert "You are Sith" in mock_ask_tool.call_args.kwargs['system_msgs'][0].content

    @pytest.mark.asyncio
    @patch("app.llm.LLM.ask_tool")
    async def test_sith_with_tools(self, mock_ask_tool):
        """Test that the Sith agent can process tool calls correctly."""
        # Create a properly structured tool call
        func = Function(name="google_search", arguments=json.dumps({"query": "What is the Sith code?"}))
        tool_call = ToolCall(id="tool-123", function=func)
        
        mock_response = MagicMock()
        mock_response.content = None
        mock_response.tool_calls = [tool_call]
        mock_ask_tool.return_value = mock_response
        
        # Mock the tool execution
        with patch("app.tool.ToolCollection.execute") as mock_execute:
            mock_execute.return_value = "Peace is a lie. There is only passion."
            
            agent = Sith(model="gpt-4")
            agent.memory.add_message(Message.user_message("Tell me the Sith code"))
            
            # Simulate a step
            result = await agent.step()
            
            # Verify the agent processed the tool call
            assert "Peace is a lie" in result or "Peace is a lie" in str(agent.messages)
            # Check that messages were correctly processed
            assert any("google_search" in str(msg) for msg in agent.messages)

    @pytest.mark.asyncio
    @patch("app.llm.LLM.ask_tool")
    async def test_sith_special_tools(self, mock_ask_tool):
        """Test the Sith agent's handling of special tools like 'terminate'."""
        # Create a properly structured tool call for the terminate tool
        func = Function(name="terminate", arguments=json.dumps({"reason": "Task completed"}))
        tool_call = ToolCall(id="tool-term-123", function=func)
        
        mock_response = MagicMock()
        mock_response.content = "I've completed the analysis."
        mock_response.tool_calls = [tool_call]
        mock_ask_tool.return_value = mock_response
        
        # Mock the tool execution and state change
        with patch("app.tool.ToolCollection.execute") as mock_execute, \
             patch("app.agent.toolcall.ToolCallAgent._handle_special_tool") as mock_handle:
            mock_execute.return_value = "Task termination confirmed."
            # Make the mock handle_special_tool actually change the state
            async def set_state_finished(*args, **kwargs):
                agent.state = AgentState.FINISHED
            mock_handle.side_effect = set_state_finished
            
            agent = Sith(model="gpt-4")
            agent.memory.add_message(Message.user_message("Analyze this data and finish"))
            
            # Simulate a step
            await agent.step()
            
            # Verify the terminate tool changed the agent state
            assert agent.state == AgentState.FINISHED 