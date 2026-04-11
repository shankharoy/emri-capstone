# Coding and Enterprise Development Standards

## Code Quality Standards

### Security
- Never hardcode secrets, API keys, or credentials in source code
- Use environment variables or secure secret management (AWS Secrets Manager, Azure Key Vault, etc.)
- Validate all user inputs to prevent injection attacks
- Follow OWASP Top 10 guidelines
- Use parameterized queries for database operations

### Code Style
- Use consistent formatting (Prettier for JS/TS, Black for Python, etc.)
- Follow language-specific style guides (Airbnb, PEP 8, Google Style)
- Maximum function length: 50 lines
- Maximum file length: 500 lines
- Prefer early returns over nested conditionals

### Testing
- Write unit tests for all business logic
- Maintain minimum 80% code coverage
- Include integration tests for API endpoints
- Use mocking for external dependencies
- Write clear test descriptions

### Documentation
- Document public APIs with JSDoc, docstrings, or equivalent
- Include README.md with setup instructions
- Document environment variables required
- Keep CHANGELOG.md updated

## Git Workflow

### Commits
- Use conventional commits format: `type(scope): description`
- Types: feat, fix, docs, style, refactor, test, chore
- Write descriptive commit messages
- Reference issue numbers when applicable

### Branches
- Main branch: `main` or `master`
- Feature branches: `feature/description`
- Bug fixes: `fix/description`
- Release branches: `release/version`

### Pull Requests
- Require code review before merging
- All CI checks must pass
- Keep PRs focused and small (< 400 lines)
- Include screenshots for UI changes

## Performance

### Frontend
- Optimize images and assets
- Use lazy loading for routes and components
- Minimize bundle size
- Implement proper caching strategies

### Backend
- Use database connection pooling
- Implement caching (Redis, Memcached)
- Optimize database queries with proper indexing
- Use pagination for large datasets

## Enterprise Considerations

### Compliance
- Ensure GDPR/privacy compliance for user data
- Implement audit logging for sensitive operations
- Follow SOC 2 compliance requirements where applicable
- Maintain data retention policies

### Monitoring
- Log errors with context (request ID, user ID)
- Use structured logging (JSON format)
- Set up alerts for critical errors
- Monitor application metrics (response time, throughput)

### Deployment
- Use infrastructure as code (Terraform, CloudFormation)
- Implement blue-green or canary deployments
- Maintain staging and production environments
- Use containerization (Docker, Kubernetes)

## Language-Specific Guidelines

### TypeScript/JavaScript
- Enable strict TypeScript mode
- Use explicit return types for functions
- Prefer `const` and `let` over `var`
- Use async/await over callbacks
- Handle all promise rejections

### Python
- Use type hints (PEP 484)
- Follow PEP 8 naming conventions
- Use virtual environments
- Pin dependency versions in requirements.txt

### Java
- Follow Java naming conventions
- Use dependency injection
- Prefer interfaces over concrete classes
- Handle exceptions properly

## Dependencies

### Security
- Regularly audit dependencies (`npm audit`, `pip-audit`)
- Keep dependencies updated
- Use only well-maintained packages
- Review license compatibility

### Management
- Use lock files (package-lock.json, yarn.lock, Pipfile.lock)
- Separate dev and production dependencies
- Document why each dependency is needed

## Error Handling

### General
- Never expose stack traces to users
- Log full error details server-side
- Return appropriate HTTP status codes
- Provide user-friendly error messages

### Retry Logic
- Implement exponential backoff
- Set maximum retry limits
- Circuit breaker pattern for external services

## API Design

### REST
- Use proper HTTP methods (GET, POST, PUT, DELETE)
- Return consistent response formats
- Version APIs (v1, v2)
- Use plural nouns for resources

### GraphQL
- Document all queries and mutations
- Use DataLoader for N+1 problem
- Implement query complexity limits

## Database

### Schema
- Use migrations for schema changes
- Never delete columns without deprecation period
- Index frequently queried columns
- Use appropriate data types

### Queries
- Avoid N+1 queries
- Use transactions for multi-step operations
- Paginate large result sets
- Sanitize all inputs

## Authentication & Authorization

### Security
- Use JWT with short expiration
- Implement refresh token rotation
- Hash passwords with bcrypt/Argon2
- Use HTTPS for all communications
- Implement rate limiting

### RBAC
- Principle of least privilege
- Regular access reviews
- Audit permission changes
