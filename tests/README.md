# Sith Tests

This directory contains the test suite for the OpenManus project. These tests verify that all agents are working correctly both individually and together.

## Test Structure

- `test_agents.py`: Basic tests for all agent classes
- `test_agent_integration.py`: Tests for agents working with tools
- `test_workflow.py`: End-to-end tests for agent workflows
- `test_sith_agent.py`: Specific tests for the Sith agent
- `test_tools.py`: Tests for the tool functionality
- `test_all_agents.py`: Comprehensive tests for all agents
- `test_memory_agent.py`: Tests for the memory agent functionality
- `test_memory_api.py`: Tests for the memory agent API endpoints
- `test_memory_e2e.py`: End-to-end tests for the memory system

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

### Memory Tests

The memory agent tests require special handling:

```bash
# Run unit tests with mocked Marqo
pytest tests/test_memory_agent.py

# Run API tests with mocked dependencies
pytest tests/test_memory_api.py

# Run end-to-end tests with actual Marqo (requires Docker)
python tests/test_memory_e2e.py

# Run integration tests with real Marqo (optional)
RUN_MARQO_TESTS=1 pytest tests/test_memory_agent.py::TestMemoryIntegration
```

## Test Coverage

The tests cover:

1. Agent initialization and basic functionality
2. Tool integration with agents
3. Agent workflows (planning and execution)
4. Tool functionality and validation
5. Edge cases and error handling
6. Memory storage and retrieval
7. Log processing and information extraction
8. API endpoints for memory operations

## Adding New Tests

When adding new agents or tools to the project, please ensure:

1. Add unit tests for the new functionality in the appropriate test file
2. Update `test_all_agents.py` to include new agent classes
3. Add integration tests if the new functionality interacts with existing components

## Mock Strategy

The tests use Python's unittest.mock to mock various dependencies:

- Mock responses are defined in fixtures
- Different mock responses are used for different test scenarios
- Tool calls are tested with appropriate mocked responses
- Marqo vector database is mocked for memory agent tests

## Test Dependencies

- pytest
- unittest.mock
- fastapi.testclient (for API tests)
- tempfile (for log processing tests) 