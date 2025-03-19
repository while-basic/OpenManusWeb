import pytest
from unittest.mock import MagicMock, patch
import json
import asyncio

from app.agent import PlanningAgent, ToolCallAgent
from app.tool import BaseTool
from app.schema import Function, Message, ToolCall
from pydantic import Field

class TestSearchTool(BaseTool):
    """Test search tool for workflow tests."""

    name: str = Field(default="search")
    description: str = Field(default="Search for information.")
    parameters: dict = Field(
        default={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        }
    )

    async def execute(self, **kwargs):
        """Execute the search tool."""
        return f"Search results for '{kwargs['query']}': Example result 1, Example result 2"


class TestActionTool(BaseTool):
    """Test action tool for workflow tests."""

    name: str = Field(default="take_action")
    description: str = Field(default="Take an action based on information.")
    parameters: dict = Field(
        default={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Action to take"},
                "data": {"type": "string", "description": "Data to act on"},
            },
            "required": ["action", "data"],
        }
    )

    async def execute(self, **kwargs):
        """Execute the action tool."""
        return f"Action '{kwargs['action']}' completed on '{kwargs['data']}'"


@pytest.fixture
def planning_response():
    """Fixture for planning agent response."""
    return {
        "id": "plan-id",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "1. Search for information using the search tool\n2. Analyze the results\n3. Take action based on the analysis",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
    }


@pytest.fixture
def search_tool_call_response():
    """Fixture for search tool call response."""
    return {
        "id": "search-call-id",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "search-call-1",
                            "type": "function",
                            "function": {
                                "name": "search",
                                "arguments": json.dumps({"query": "test query"}),
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
def action_tool_call_response():
    """Fixture for action tool call response."""
    return {
        "id": "action-call-id",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "action-call-1",
                            "type": "function",
                            "function": {
                                "name": "take_action",
                                "arguments": json.dumps(
                                    {"action": "process", "data": "Example result 1"}
                                ),
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
def final_response():
    """Fixture for final agent response."""
    return {
        "id": "final-id",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "I have completed the workflow by: 1) Searching for 'test query', 2) Analyzing the results, and 3) Taking the 'process' action on 'Example result 1'.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 15, "completion_tokens": 15, "total_tokens": 30},
    }


class TestAgentWorkflow:
    """Tests for agent workflows."""

    @pytest.mark.asyncio
    async def test_planning_and_execution_workflow(self):
        """Test a planning agent creating a plan and a tool agent executing it."""
        # Create a planning agent
        planning_agent = PlanningAgent(
            system_prompt="You are a planning agent. Create a step-by-step plan.",
            model="gpt-4"
        )

        # Create tools for the execution agent
        search_tool = TestSearchTool()
        action_tool = TestActionTool()

        # Create an execution agent
        execution_agent = ToolCallAgent(
            system_prompt="You are an execution agent. Execute the plan step by step.",
            model="gpt-4"
        )

        # Add tools to the execution agent
        execution_agent.available_tools.tool_map["search"] = search_tool
        execution_agent.available_tools.tool_map["take_action"] = action_tool

        # Create tool calls for testing
        search_function = Function(name="search", arguments=json.dumps({"query": "test query"}))
        search_tool_call = ToolCall(id="search-call-1", type="function", function=search_function)
        
        action_function = Function(
            name="take_action", 
            arguments=json.dumps({"action": "process", "data": "Example result 1"})
        )
        action_tool_call = ToolCall(id="action-call-1", type="function", function=action_function)

        # Step 1: Get a plan from the planning agent
        with patch.object(planning_agent, 'step', return_value="1. Search for information\n2. Take action") as mock_planning_step:
            # Add a message to start planning
            planning_agent.memory.add_message(Message.user_message("Create a plan to search for information and take action"))
            plan = await planning_agent.run("Create a plan to search for information and take action")
            
            # Verify the plan was created
            assert mock_planning_step.call_count >= 1
            assert "Search for information" in plan

        # Step 2: Execute the plan with the execution agent
        # Define custom patched methods that update memory correctly
        async def patched_think():
            nonlocal execution_agent, step
            if step == 1:
                # First call: set up search tool call
                execution_agent.tool_calls = [search_tool_call]
                # Add the tool call message to memory
                execution_agent.memory.add_message(
                    Message(role="assistant", content=None, tool_calls=[search_tool_call])
                )
                return True
            elif step == 2:
                # Second call: set up action tool call
                execution_agent.tool_calls = [action_tool_call]
                # Add the tool call message to memory
                execution_agent.memory.add_message(
                    Message(role="assistant", content=None, tool_calls=[action_tool_call])
                )
                return True
            else:
                # Final call: no more tools
                execution_agent.memory.add_message(
                    Message.assistant_message("Workflow completed successfully.")
                )
                return False
                
        async def patched_act():
            nonlocal execution_agent, step
            if step == 1:
                # First step: search tool result
                result = "Search results for 'test query': Example result 1, Example result 2"
                # Add result to memory as tool message
                execution_agent.memory.add_message(
                    Message.tool_message(
                        content=result,
                        name="search",
                        tool_call_id=search_tool_call.id
                    )
                )
                step += 1
                return result
            elif step == 2:
                # Second step: action tool result
                result = "Action 'process' completed on 'Example result 1'"
                # Add result to memory as tool message
                execution_agent.memory.add_message(
                    Message.tool_message(
                        content=result,
                        name="take_action",
                        tool_call_id=action_tool_call.id
                    )
                )
                step += 1
                return result
            else:
                return "No more tools to execute"
        
        # Set up step counter
        step = 1
        
        # Mock the execution agent's methods
        with patch.object(execution_agent, 'think', side_effect=patched_think) as mock_think:
            with patch.object(execution_agent, 'act', side_effect=patched_act) as mock_act:
                # Set up the execution agent with the plan
                execution_agent.memory.add_message(Message.user_message(f"Execute this plan:\n{plan}"))
                
                # Run the execution agent
                result = await execution_agent.run(f"Execute this plan:\n{plan}")
                
                # Verify the execution
                assert mock_think.call_count >= 2
                assert mock_act.call_count >= 2
                
                # Check messages in memory
                search_messages = [m.content for m in execution_agent.memory.messages 
                                if m.content and "Search results" in m.content]
                action_messages = [m.content for m in execution_agent.memory.messages 
                                if m.content and "Action" in m.content]
                
                assert len(search_messages) >= 1, "Search result not found in agent memory"
                assert len(action_messages) >= 1, "Action result not found in agent memory" 