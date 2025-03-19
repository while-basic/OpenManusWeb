# Sith Tests

This directory contains the test suite for the OpenManus project. These tests verify that all agents are working correctly both individually and together.

## Test Structure

- `test_agents.py`: Basic tests for all agent classes
- `test_agent_integration.py`: Tests for agents working with tools
- `test_workflow.py`: End-to-end tests for agent workflows
- `test_sith_agent.py`: Specific tests for the Sith agent
- `test_tools.py`: Tests for the tool functionality
- `test_all_agents.py`: Comprehensive tests for all agents

## Running Tests

You can run all tests with:

```bash
pytest
```

Or run specific test files:

```bash
pytest tests/test_agents.py
```

Or run tests with specific markers:

```bash
pytest -m "slow"  # Run slow tests
```

## Test Coverage

The tests cover:

1. Agent initialization and basic functionality
2. Tool integration with agents
3. Agent workflows (planning and execution)
4. Tool functionality and validation
5. Edge cases and error handling

## Adding New Tests

When adding new agents or tools to the project, please ensure:

1. Add unit tests for the new functionality in the appropriate test file
2. Update `test_all_agents.py` to include new agent classes
3. Add integration tests if the new functionality interacts with existing components

## Mock Strategy

The tests use Python's unittest.mock to mock the OpenAI API calls:

- Mock responses are defined in fixtures
- Different mock responses are used for different test scenarios
- Tool calls are tested with appropriate mocked responses

## Test Dependencies

- pytest
- unittest.mock 