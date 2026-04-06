# OpenRouter Client Tests

## Test Coverage

- `test_openrouter_client.py`: Unit tests for OpenRouterClient
  - Config loading from env
  - Model alias resolution
  - Health check
  - Chat completion (mocked)
  - Error handling

## Running Tests

```bash
pytest modules/infrastructure/openrouter_client/tests -v
```

## Test Requirements

Tests use mocked responses and don't require a valid API key.
Set `OPENROUTER_API_KEY=test-key` for tests that check config loading.
