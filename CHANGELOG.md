# Changelog

## 0.2.0

Easier to start, safer to run against real servers, and ready for CI.

- `s1kit init` writes a starter suite to `s1kit.yaml`, and `s1kit test` runs it with no arguments.
- `s1kit test -j N` sends N requests at a time. Results keep suite order, so runs diff cleanly.
- `s1kit test` and `s1kit report` end with one accuracy line per provider, most accurate first.
- HTTP providers retry 429, 5xx and dropped connections with backoff and honour `Retry-After`
  (`retries:` in the suite, default 2). Errors now say what went wrong: an unreachable server,
  a timeout, an HTTP status with the server's message, a missing API key on a 401, or a reply
  that is not JSON.
- `model:` is optional for HTTP providers, so laya-serve can pick its own checkpoint.
- GitHub Action: `uses: Eliot5566/s1kit@v0.2.0` runs a suite, writes the table to the job summary
  and fails below `fail-under`.
- The example suite points at laya-serve's default port (8000).
- Tests run the HTTP provider against a local server that answers like laya-serve.

## 0.1.0

First release.

- `s1kit test` runs a YAML suite against any `/v1/systemone` provider and saves every decision to `results.jsonl`.
- `s1kit report` prints accuracy and p50/p95 latency per provider and question.
- `s1kit calibrate` writes `thresholds.yaml` with the lowest confidence cutoff that reaches a target precision.
- `s1kit.Router` asks the cheapest provider first and escalates below the calibrated cutoff.
- Built-in `keyword` baseline provider, so the example suite runs offline.
