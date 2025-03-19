import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import importlib

from app.agent import BaseAgent, PlanningAgent, ReActAgent, SWEAgent, ToolCallAgent
from app.agent.sith import Sith
from tests.test_agents import TestableBaseAgent, TestableReActAgent

# List of all agents in the codebase with concrete classes for abstract ones
AGENTS = [
    TestableBaseAgent,  # Concrete implementation for testing
    PlanningAgent, 
    TestableReActAgent,  # Concrete implementation for testing
    SWEAgent,
    ToolCallAgent,
    Sith
]

@pytest.mark.parametrize("agent_class", AGENTS)
def test_agent_initialization(agent_class):
    """Test that all agents can be initialized with basic parameters."""
    agent = agent_class(
        system_prompt="You are a test agent",
        model="gpt-4"
    )
    assert agent.system_prompt == "You are a test agent"
    assert agent.model == "gpt-4"

@pytest.mark.parametrize("agent_class", AGENTS)
def test_agent_has_run_method(agent_class):
    """Test that all agents have a run method."""
    agent = agent_class(
        system_prompt="You are a test agent",
        model="gpt-4"
    )
    assert hasattr(agent, "run")
    assert callable(agent.run)

@pytest.mark.parametrize("agent_class", [cls for cls in AGENTS if hasattr(cls, "available_tools") or "ToolCallAgent" in cls.__name__])
def test_tool_support(agent_class):
    """Test that agents supporting tools have the necessary tool handling capabilities."""
    # Create a test agent
    agent = agent_class(
        system_prompt="You are a test agent",
        model="gpt-4"
    )
    
    # Check for appropriate tool-related attributes
    if hasattr(agent, "available_tools"):
        assert hasattr(agent.available_tools, "tool_map")
        assert isinstance(agent.available_tools.tool_map, dict)
    
    # Verify the agent can handle tool-related functionality
    assert hasattr(agent, "execute_tool") or hasattr(agent, "act"), "Agent should have execute_tool or act method"
    
    # Test basic tool execution flow for tool-specific agents
    if agent_class.__name__ == "ToolCallAgent":
        assert hasattr(agent, "think"), "ToolCallAgent should have a think method"
        assert hasattr(agent, "act"), "ToolCallAgent should have an act method"

@pytest.mark.parametrize("module_name", [
    "test_agents",
    "test_agent_integration",
    "test_workflow", 
    "test_sith_agent"
])
def test_import_test_modules(module_name):
    """Test that all test modules can be imported."""
    try:
        module = importlib.import_module(f"tests.{module_name}")
        assert module is not None
    except ImportError as e:
        pytest.fail(f"Failed to import {module_name}: {str(e)}")

def test_all_test_files_have_tests():
    """Test that all test files have pytest test classes or functions."""
    for module_name in ["test_agents", "test_agent_integration", "test_workflow", "test_sith_agent"]:
        module = importlib.import_module(f"tests.{module_name}")
        
        # Check if module has test classes
        has_tests = False
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            
            # Check if it's a class and starts with Test
            if isinstance(attr, type) and attr_name.startswith("Test"):
                has_tests = True
                break
            
            # Check if it's a function and starts with test_
            if callable(attr) and attr_name.startswith("test_"):
                has_tests = True
                break
        
        assert has_tests, f"Module {module_name} doesn't contain any test classes or functions"

@pytest.mark.asyncio
@patch("app.llm.LLM.ask")
async def test_mock_response_format(mock_ask):
    """Test that our mock response format works with all agents."""
    # Create a standard mock response that all agents should handle
    mock_ask.return_value = "Test response"
    
    # This tests a concrete implementation of BaseAgent
    agent = TestableBaseAgent(
        system_prompt="You are a test agent",
        model="gpt-4"
    )
    
    # Patch the step method directly
    with patch.object(TestableBaseAgent, 'step', return_value="Test response") as mock_step:
        response = await agent.run("Test query")
        assert "Test" in response
        mock_step.assert_called() 