# Unit / Contract Tests

## Files
- `tests/test_agents.py`
- `tests/test_api.py`

## Purpose
Fast unit/contract tests using mocks. They validate config parsing, planner output, manager flow, and API wiring without requiring Milvus or model downloads.

## Run

```bash
python -m unittest tests.test_agents tests.test_api
```
