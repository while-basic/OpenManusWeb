# OpenManusWeb Codebase Rules

This directory contains guidelines for maintaining and developing the OpenManusWeb codebase. These rules help ensure consistency, quality, and maintainability across the project.

## Rules Index

1. **[General Guidelines](01_general_guidelines.md)**
   - Code structure, naming conventions, documentation, error handling, async programming, and dependencies

2. **[LLM Integration](02_llm_integration.md)**
   - Configuration, tool format handling, prompts, error handling, Ollama specifics, and testing

3. **[Web Application](03_web_application.md)**
   - Event loop management, frontend, API design, WebSockets, security, performance, and deployment

4. **[Tool Development](04_tool_development.md)**
   - Structure, documentation, error handling, testing, parameters, security, and performance

## Key Principles

1. **Maintainability**: Write code that is easy to understand and modify
2. **Modularity**: Keep components focused and loosely coupled
3. **Error Resilience**: Handle errors gracefully at all levels
4. **Performance**: Optimize for responsiveness and resource efficiency
5. **Security**: Protect user data and system integrity
6. **Documentation**: Document code, APIs, and processes thoroughly

## Common Pitfalls to Avoid

1. Mixing asyncio with synchronous code improperly
2. Failing to handle complex LLM response formats
3. Not validating inputs and outputs
4. Ignoring error conditions
5. Hardcoding configuration values
6. Not handling WebSocket connections properly 