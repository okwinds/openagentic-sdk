# HTTP Server Invalid JSON Handling

## Summary

The OpenAgentic HTTP server accepts JSON request bodies for multiple endpoints. Previously, malformed JSON could bubble up as a `json.JSONDecodeError` and be returned as a 500. This is noisy for clients and makes error handling inconsistent.

## Behavior

Requests with invalid JSON now return:

- HTTP 400 with body `{"error": "invalid_json"}`

Requests with `Content-Length` larger than the configured limit still return:

- HTTP 413 with body `{"error": "payload_too_large"}`

## Implementation Notes

- `_read_json()` now raises `ValueError("invalid_json")` for parse errors.
- Endpoints use `_read_json_or_write_error()` to map body-read failures into consistent HTTP responses.

