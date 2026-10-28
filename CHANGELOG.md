# Changelog

## 0.1.0

First release.

- `s1kit test` runs a YAML suite against any `/v1/systemone` provider and saves every decision to `results.jsonl`.
- `s1kit report` prints accuracy and p50/p95 latency per provider and question.
- `s1kit calibrate` writes `thresholds.yaml` with the lowest confidence cutoff that reaches a target precision.
- `s1kit.Router` asks the cheapest provider first and escalates below the calibrated cutoff.
- Built-in `keyword` baseline provider, so the example suite runs offline.
