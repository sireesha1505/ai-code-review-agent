# Repository Coding Guidelines

## Python

- Use type hints for function parameters and return values.
- Prefer async functions for I/O-bound operations.
- Use Pydantic models for API request and response validation.
- Do not expose database credentials or API keys in source code.
- Use parameterized queries for database operations.
- Raise meaningful exceptions instead of silently ignoring errors.

## FastAPI

- Keep route handlers thin.
- Business logic should live in service functions or service classes.
- Use dependency injection for database sessions.
- API responses should use Pydantic response models.

## Testing

- Every new business-logic function should have unit tests.
- Test important edge cases and error paths.
- Mock external APIs in unit tests.

## Code Quality

- Avoid unnecessary code duplication.
- Keep functions focused on one responsibility.
- Prefer readable code over clever code.