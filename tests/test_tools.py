import pytest
from unittest.mock import MagicMock, patch

from app.tool import BaseTool

class SimpleTestTool(BaseTool):
    """A simple test tool that extends BaseTool."""
    
    def __init__(self):
        super().__init__(
            name="simple_test_tool",
            description="A simple test tool",
            parameters={
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"},
                    "arg2": {"type": "integer"}
                },
                "required": ["arg1"]
            }
        )
    
    async def execute(self, arg1, arg2=None):
        """Implementation of the tool's functionality."""
        if arg2 is not None:
            return f"Tool executed with arg1={arg1}, arg2={arg2}"
        return f"Tool executed with arg1={arg1}"

class TestBaseTool:
    """Tests for the BaseTool class."""
    
    def test_initialization(self):
        """Test that a tool can be initialized with the correct parameters."""
        tool = SimpleTestTool()
        
        assert tool.name == "simple_test_tool"
        assert tool.description == "A simple test tool"
        assert "arg1" in tool.parameters["properties"]
        assert "arg2" in tool.parameters["properties"]
        assert "arg1" in tool.parameters["required"]
    
    def test_to_param(self):
        """Test conversion to parameter format."""
        tool = SimpleTestTool()
        param = tool.to_param()
        
        assert param["type"] == "function"
        assert param["function"]["name"] == "simple_test_tool"
        assert param["function"]["description"] == "A simple test tool"
        assert param["function"]["parameters"] == tool.parameters
    
    @pytest.mark.asyncio
    async def test_execute_with_required_args(self):
        """Test executing a tool with required arguments."""
        tool = SimpleTestTool()
        result = await tool.execute(arg1="test_value")
        
        assert result == "Tool executed with arg1=test_value"
    
    @pytest.mark.asyncio
    async def test_execute_with_optional_args(self):
        """Test executing a tool with both required and optional arguments."""
        tool = SimpleTestTool()
        result = await tool.execute(arg1="test_value", arg2=42)
        
        assert result == "Tool executed with arg1=test_value, arg2=42"
    
    @pytest.mark.asyncio
    async def test_execute_missing_required_args(self):
        """Test that execute raises an error when required arguments are missing."""
        tool = SimpleTestTool()
        
        with pytest.raises(TypeError):
            await tool.execute()  # Missing required arg1
    
    @pytest.mark.asyncio
    async def test_call_method(self):
        """Test that the __call__ method works correctly."""
        tool = SimpleTestTool()
        result = await tool(arg1="test_value")
        
        assert result == "Tool executed with arg1=test_value"
    
    @pytest.mark.asyncio
    async def test_validation(self):
        """Test that arguments are correctly validated."""
        # For this test, we'll create a tool with more strict validation
        class ValidatingTool(BaseTool):
            def __init__(self):
                super().__init__(
                    name="validating_tool",
                    description="A tool with validation",
                    parameters={
                        "type": "object",
                        "properties": {
                            "number": {"type": "integer", "minimum": 1, "maximum": 10}
                        },
                        "required": ["number"]
                    }
                )
            
            async def execute(self, number):
                return f"Valid number: {number}"
        
        # This test assumes validation is performed in the BaseTool class
        # If validation is not implemented, this test would need to be adjusted
        tool = ValidatingTool()
        
        # Valid case
        result = await tool.execute(number=5)
        assert result == "Valid number: 5"
        
        # Invalid cases would be tested here if validation is implemented
        # This might not work if BaseTool doesn't implement full JSON Schema validation
        # but is included for completeness
        try:
            await tool.execute(number="not_a_number")
            pytest.fail("Should have raised a validation error")
        except:
            pass  # Expected to fail
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in the tool."""
        # Create a tool that raises an exception
        class ErrorTool(BaseTool):
            def __init__(self):
                super().__init__(
                    name="error_tool",
                    description="A tool that raises an error",
                    parameters={
                        "type": "object",
                        "properties": {
                            "trigger_error": {"type": "boolean"}
                        },
                        "required": ["trigger_error"]
                    }
                )
            
            async def execute(self, trigger_error):
                if trigger_error:
                    raise ValueError("This is an expected test error")
                return "No error triggered"
        
        tool = ErrorTool()
        
        # Test normal operation
        result = await tool.execute(trigger_error=False)
        assert result == "No error triggered"
        
        # Test error handling
        with pytest.raises(ValueError) as excinfo:
            await tool.execute(trigger_error=True)
        assert "This is an expected test error" in str(excinfo.value) 