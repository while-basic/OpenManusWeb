import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from typing import Optional

from app.agent.base import BaseAgent
from app.schema import Message, AgentState
from pydantic import Field


class MockAgent(BaseAgent):
    """
    A concrete implementation of BaseAgent for testing purposes.
    
    This class provides a minimal implementation of the abstract BaseAgent
    for testing without requiring connections to external services.
    """
    
    name: str = Field(default="MockAgent")
    description: Optional[str] = Field(default="A test agent")
    
    async def step(self):
        """
        Implement the required abstract method to return a test response.
        """
        # Set state to FINISHED after the first step to prevent multiple steps
        if self.current_step == 1:
            self.state = AgentState.FINISHED
            return f"Step {self.current_step}: Mock step response"
        return f"Step {self.current_step}: Mock step response"


@pytest.mark.asyncio
class TestMockAgent:
    """Tests for a minimal BaseAgent implementation."""
    
    @patch("app.llm.LLM.ask")
    async def test_agent_initialization(self, mock_ask):
        """Test that an agent can be initialized with basic parameters."""
        # Mock the LLM ask method to avoid API calls
        mock_ask.return_value = "Test response"
        
        agent = MockAgent(
            system_prompt="You are a test agent",
            model="gpt-4",
            temperature=0.7
        )
        
        assert agent.system_prompt == "You are a test agent"
        assert agent.model == "gpt-4"
        assert agent.temperature == 0.7
        assert agent.name == "MockAgent"
        assert agent.description == "A test agent"
    
    @patch("app.llm.LLM.ask")
    async def test_agent_run_method(self, mock_ask):
        """Test that agent.run() correctly processes a user request."""
        # Mock the LLM ask method to return a test response
        mock_ask.return_value = "Test response"
        
        agent = MockAgent(
            system_prompt="You are a test agent",
            model="gpt-4",
            max_steps=1  # Limit to a single step
        )
        
        response = await agent.run("Test message")
        
        # The run method concatenates step results with "Step X: " prefixes
        assert "Mock step response" in response
        assert "Step 1:" in response
        
        # Check that the user message was added to memory
        assert len(agent.memory.messages) > 0
        assert any(msg.role == "user" and msg.content == "Test message" for msg in agent.memory.messages)
    
    @patch("app.llm.LLM.ask")
    async def test_agent_memory_management(self, mock_ask):
        """Test that agent properly manages its memory."""
        mock_ask.return_value = "Memory test response"
        
        agent = MockAgent(
            system_prompt="You are a test agent",
            model="gpt-4"
        )
        
        # Add a test message to memory
        agent.update_memory("user", "Test memory")
        
        # Verify message was added
        assert len(agent.memory.messages) > 0
        assert any(msg.role == "user" and msg.content == "Test memory" for msg in agent.memory.messages)
        
        # Test clearing memory
        agent.memory.clear()
        assert len(agent.memory.messages) == 0
    
    @patch("app.llm.LLM.ask")
    async def test_agent_state_context(self, mock_ask):
        """Test agent state transition context manager."""
        mock_ask.return_value = "State test response"
        
        agent = MockAgent(
            system_prompt="You are a test agent",
            model="gpt-4"
        )
        
        # Test state transition
        async with agent.state_context(AgentState.RUNNING):
            assert agent.state == AgentState.RUNNING
        
        # State should return to IDLE after context
        assert agent.state == AgentState.IDLE
    
    @patch("app.llm.LLM.ask")
    async def test_agent_step_method(self, mock_ask):
        """Test the agent's step method."""
        mock_ask.return_value = "Step test response"
        
        agent = MockAgent(
            system_prompt="You are a test agent",
            model="gpt-4"
        )
        
        # Call step method directly
        result = await agent.step()
        assert result == f"Step {agent.current_step}: Mock step response" 