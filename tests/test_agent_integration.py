import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.schema import Function, Message, ToolCall
from app.tool.base import BaseTool


class TestTool(BaseTool):
    """A test tool for integration tests."""

    name: str = Field(default="test_tool")
    description: str = Field(default="A test tool.")
    parameters: dict = Field(
        default={
            "type": "object",
            "properties": {
                "arg1": {"type": "string", "description": "Test argument"}
            },
            "required": ["arg1"],
        }
    )

    async def execute(self, **kwargs):
        """Execute the test tool."""
        return f"Tool executed with argument: {kwargs['arg1']}"


class TestAgentToolIntegration:
    """Tests for agent-tool integration."""

    @pytest.fixture
    def tool_call_response(self):
        """Return a mock tool call response."""
        return {
            "id": "test-id",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_123",
                                "type": "function",
                                "function": {
                                    "name": "test_tool",
                                    "arguments": json.dumps({"arg1": "test_value"}),
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        }

    @pytest.fixture
    def tool_observation_response(self):
        """Return a mock tool observation response."""
        return {
            "id": "test-id-2",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "I used the test tool and got: Tool executed with argument: test_value",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 15, "completion_tokens": 15, "total_tokens": 30},
        }

    @pytest.mark.asyncio
    async def test_agent_using_tool(self):
        """Test that an agent can use tools properly."""
        # Create a test tool
        test_tool = TestTool()

        # Create a tool-using agent
        agent = ToolCallAgent(
            system_prompt="You are a tool-using agent",
            model="gpt-4"
        )

        # Add the test tool to the agent's available tools
        agent.available_tools.tool_map["test_tool"] = test_tool

        # Create proper tool call message for first response
        function = Function(name="test_tool", arguments=json.dumps({"arg1": "test_value"}))
        tool_call = ToolCall(id="call_123", type="function", function=function)
        tool_call_message = Message(role="assistant", content=None, tool_calls=[tool_call])
        
        # Create observation message for second response
        observation_message = Message(
            role="assistant", 
            content="I used the test tool and got: Tool executed with argument: test_value"
        )
        
        # Mock the think and act methods instead of LLM.ask_tool
        with patch.object(agent, 'think', return_value=True) as mock_think:
            # Use a separate mock for the execute_tool method
            with patch.object(agent, 'execute_tool', return_value="Tool executed with argument: test_value") as mock_execute:
                # Add a user message to the agent's memory
                agent.memory.add_message(Message.user_message("Use the test tool with arg1=test_value"))
                
                # Override tool_calls for the test
                agent.tool_calls = [tool_call]
                
                # Run the agent
                response = await agent.run("Use the test tool with arg1=test_value")
                
                # Verify the result
                assert "executed with argument: test_value" in response
                assert mock_think.call_count >= 1
                assert mock_execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_multiple_tool_calls(self):
        """Test that an agent can make multiple tool calls in sequence."""
        # Create a test tool
        test_tool = TestTool()

        # Create a tool-using agent
        agent = ToolCallAgent(
            system_prompt="You are a tool-using agent",
            model="gpt-4",
            max_steps=3  # Allow up to 3 steps
        )

        # Add the test tool to the agent's available tools
        agent.available_tools.tool_map["test_tool"] = test_tool
        
        # Create first tool call
        first_function = Function(name="test_tool", arguments=json.dumps({"arg1": "first_call"}))
        first_tool_call = ToolCall(id="call_1", type="function", function=first_function)
        
        # Create second tool call
        second_function = Function(name="test_tool", arguments=json.dumps({"arg1": "second_call"}))
        second_tool_call = ToolCall(id="call_2", type="function", function=second_function)

        # Add a message to start the conversation
        agent.memory.add_message(Message.user_message("Make multiple tool calls"))
        
        # Define patched methods to properly modify agent memory
        async def patched_think():
            nonlocal agent, agent_step
            if agent_step == 1:
                # First tool call
                agent.tool_calls = [first_tool_call]
                agent_tool_call = first_tool_call
                return True
            elif agent_step == 2:
                # Second tool call
                agent.tool_calls = [second_tool_call]
                agent_tool_call = second_tool_call
                return True
            else:
                # No more tools
                return False
                
        async def patched_act():
            nonlocal agent, agent_step
            if agent_step == 1:
                result = "First tool result"
                # Add result to memory as an assistant message
                agent.memory.add_message(Message.assistant_message(result))
                agent_step += 1
                return result
            elif agent_step == 2:
                result = "Second tool result"
                # Add result to memory as an assistant message
                agent.memory.add_message(Message.assistant_message(result))
                agent_step += 1
                return result
            else:
                return "No more tool calls"
        
        # Track which step we're on
        agent_step = 1
        agent_tool_call = None
        
        # Mock the agent's think and act methods
        with patch.object(agent, 'think', side_effect=patched_think) as mock_think:
            with patch.object(agent, 'act', side_effect=patched_act) as mock_act:
                # Run the agent
                response = await agent.run("Make multiple tool calls")
                
                # Verify the results
                assert mock_think.call_count >= 2
                assert mock_act.call_count >= 2
                
                # Check for messages in memory
                messages = [m.content for m in agent.memory.messages if m.content and "tool result" in m.content]
                assert len(messages) >= 2
                assert any("First tool result" in m for m in messages)
                assert any("Second tool result" in m for m in messages) 