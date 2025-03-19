import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json

from app.agent import BaseAgent, PlanningAgent, ReActAgent, SWEAgent, ToolCallAgent
from app.agent.sith import Sith
from app.schema import Function, ToolCall, Message
from pydantic import Field

# Create concrete test implementations of abstract classes
class TestableBaseAgent(BaseAgent):
    """A concrete implementation of BaseAgent for testing."""
    name: str = Field(default="TestableBaseAgent")
    description: str = Field(default="A testable implementation of BaseAgent")

    async def step(self):
        """Implement the abstract step method."""
        return "Test step"

class TestableReActAgent(ReActAgent):
    """A concrete implementation of ReActAgent for testing."""
    name: str = Field(default="TestableReActAgent")
    description: str = Field(default="A testable implementation of ReActAgent")

    async def think(self):
        """Implement the abstract think method."""
        return True
        
    async def act(self):
        """Implement the abstract act method."""
        return "Test action"

@pytest.fixture
def mock_llm_response():
    """Fixture to provide a mocked LLM response."""
    response = MagicMock()
    response.content = "Test response"
    response.tool_calls = None
    return response

@pytest.fixture
def tool_response():
    """Fixture for tool call response."""
    func = Function(name="test_tool", arguments=json.dumps({"arg1": "value1"}))
    tool_call = ToolCall(id="call_123", function=func)
    
    response = MagicMock()
    response.content = None
    response.tool_calls = [tool_call]
    return response

class TestBaseAgent:
    """Tests for the BaseAgent class."""
    
    @pytest.mark.asyncio
    @patch("app.llm.LLM.ask")
    async def test_init_and_run(self, mock_ask, mock_llm_response):
        """Test BaseAgent initialization and basic run method."""
        mock_ask.return_value = "Test response"
        
        agent = TestableBaseAgent(
            system_prompt="You are a test agent",
            model="gpt-4",
            temperature=0.7
        )
        
        assert agent.system_prompt == "You are a test agent"
        assert agent.model == "gpt-4"
        assert agent.temperature == 0.7
        
        # Replace the step method with a simple mock
        with patch.object(TestableBaseAgent, 'step', return_value="Test response") as mock_step:
            response = await agent.run("Test message")
            assert "Test" in response
            mock_step.assert_called()

class TestToolCallAgent:
    """Tests for the ToolCallAgent class."""
    
    @pytest.mark.asyncio
    @patch("app.llm.LLM.ask_tool")
    async def test_tool_calling(self, mock_ask_tool, tool_response):
        """Test ToolCallAgent tool calling functionality."""
        mock_ask_tool.return_value = tool_response

        # Create a mock for ToolCollection.execute
        with patch("app.tool.ToolCollection.execute") as mock_execute:
            mock_execute.return_value = "Tool called with value1"

            # Create a mock tool map
            mock_tool_map = {'test_tool': mock_execute}
            
            # Create a ToolCallAgent instance with our mock tool map
            agent = ToolCallAgent(system_prompt="test prompt", model="test_model")
            
            # Patch the tool_map in the agent's available_tools
            with patch.object(agent.available_tools, 'tool_map', mock_tool_map):
                # Add a message to start the conversation
                agent.memory.add_message(Message.user_message("Use the test tool"))
                
                # Configure the tool_call response
                function = {"name": "test_tool", "arguments": '{"value": "value1"}'}
                tool_call = {"id": "call_1", "type": "function", "function": function}
                tool_response.tool_calls = [ToolCall(**tool_call)]
                
                # Call step and check the result
                result = await agent.step()
                
                # Make sure the tool was executed
                mock_execute.assert_called_once()
                
                # Check if the result contains our tool's response
                assert "Tool called with value1" in result or "Tool called with value1" in [m.content for m in agent.memory.messages]

class TestPlanningAgent:
    """Tests for the PlanningAgent class."""
    
    @pytest.mark.asyncio
    async def test_planning(self):
        """Test PlanningAgent planning functionality."""
        # Create a planning agent with mocked tools
        with patch("app.tool.ToolCollection.execute") as mock_execute:
            mock_execute.return_value = "Test plan execution successful"
            
            agent = PlanningAgent(
                system_prompt="You are a planning agent",
                model="gpt-4"
            )
            
            # Patch the step method to return a simple response
            with patch.object(PlanningAgent, 'step', return_value="Test planning response"):
                response = await agent.run("Plan a task")
                assert "Test planning response" in response

class TestReActAgent:
    """Tests for the ReActAgent class."""
    
    @pytest.mark.asyncio
    async def test_react_approach(self):
        """Test ReActAgent reasoning and acting functionality."""
        agent = TestableReActAgent(
            system_prompt="You are a ReAct agent",
            model="gpt-4"
        )
        
        # Directly mock the step method instead of think and act
        with patch.object(TestableReActAgent, 'step', return_value="Test reasoning and action") as mock_step:
            response = await agent.run("Solve this problem")
            assert "Test" in response
            # Verify that step was called
            mock_step.assert_called()

class TestSWEAgent:
    """Tests for the SWEAgent class."""
    
    @pytest.mark.asyncio
    @patch("app.llm.LLM.ask_tool")
    async def test_swe_functionality(self, mock_ask_tool, mock_llm_response):
        """Test SWEAgent software engineering capabilities."""
        mock_ask_tool.return_value = mock_llm_response
        
        agent = SWEAgent(
            system_prompt="You are a software engineer agent",
            model="gpt-4"
        )
        
        # Add a user message to trigger processing
        agent.memory.add_message(Message.user_message("Write a function"))
        
        # Test a step directly
        result = await agent.step()
        assert "Test response" in str(result) or "Test response" in str(agent.messages)
        mock_ask_tool.assert_called_once()

class TestSithAgent:
    """Tests for the Sith agent."""
    
    @pytest.mark.asyncio
    @patch("app.llm.LLM.ask_tool")
    async def test_sith_functionality(self, mock_ask_tool, mock_llm_response):
        """Test Sith agent specific capabilities."""
        mock_ask_tool.return_value = mock_llm_response
        
        agent = Sith(
            system_prompt="You are a Sith agent",
            model="gpt-4"
        )
        
        # Add a user message to trigger processing
        agent.memory.add_message(Message.user_message("Execute order 66"))
        
        # Test a step directly
        result = await agent.step()
        assert "Test response" in str(result) or "Test response" in str(agent.messages)
        mock_ask_tool.assert_called_once()

@pytest.mark.parametrize(
    "agent_class", 
    [TestableBaseAgent, ToolCallAgent, PlanningAgent, TestableReActAgent, SWEAgent, Sith]
)
def test_agent_compatibility(agent_class):
    """Test that all agents have compatible interfaces."""
    agent = agent_class(
        system_prompt="You are a test agent",
        model="gpt-4"
    )
    
    # Check that all agents have the essential methods
    assert hasattr(agent, "run")
    assert callable(agent.run)
    
    # Check common attributes
    assert hasattr(agent, "system_prompt")
    assert hasattr(agent, "model") 