# Real-API End-to-End Tests

These tests call a real OpenAI-compatible API endpoint (default: RIGHTCODE) and verify `openagentic_sdk` behavior end-to-end.

## Requirements

- Python 3.11+
- Network access to your configured endpoint
- Env vars:
  - `RIGHTCODE_API_KEY` (required)
  - `RIGHTCODE_BASE_URL` (optional, default `https://www.right.codes/codex/v1`)
  - `RIGHTCODE_MODEL` (optional, default `gpt-5.2`)
  - `RIGHTCODE_TIMEOUT_S` (optional, default `120`)

## Run

Run all e2e tests:

`python3 -m unittest discover -s e2e_tests -p "e2e_*.py" -v`

Notes:
- The unit test command `python3 -m unittest -q` does not include these tests (pattern mismatch).
- These tests may incur real model costs.

