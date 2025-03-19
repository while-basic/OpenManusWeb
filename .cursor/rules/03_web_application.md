# Web Application Guidelines

## Event Loop Management
- Do not use `asyncio.run()` to start the web server
- Let Uvicorn manage its own event loop
- Keep FastAPI endpoints asynchronous
- Handle WebSocket connections properly

## Frontend
- Keep JavaScript modular and organized
- Use modern ES6+ syntax with appropriate polyfills
- Maintain responsive design principles
- Implement progressive enhancement

## API Design
- Follow RESTful design principles
- Provide clear error responses
- Document API endpoints with OpenAPI/Swagger
- Version APIs appropriately

## WebSockets
- Implement proper connection handling
- Handle reconnection gracefully
- Provide status updates through WebSockets
- Implement proper error handling

## Security
- Validate all user inputs
- Implement appropriate rate limiting
- Use HTTPS in production
- Sanitize outputs to prevent XSS

## Performance
- Optimize database queries
- Implement caching where appropriate
- Minimize client-side JavaScript
- Use async where it improves performance

## Deployment
- Document deployment steps clearly
- Support containerized deployment
- Provide health check endpoints
- Implement proper logging for production 