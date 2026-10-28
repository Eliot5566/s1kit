# s1kit

**Test, calibrate and route System One decision models on your own data.**

[繁體中文說明](README.zh-TW.md)

Decision models (Jev, Laya, kev, and anything served by llama.cpp or Ollama) all
speak the same `/v1/systemone` API and return typed answers with a confidence.
s1kit answers the three questions you hit on day one:

1. **Which model is most accurate on _my_ data?** `s1kit test` runs one suite against every model side by side.
2. **What confidence can I trust?** `s1kit calibrate` picks a cutoff per question that reaches your target precision.
3. **What happens below that cutoff?** `s1kit.Router` asks the cheapest model first and escalates only when it is unsure.

```
$ s1kit test examples/support-tickets.yaml
provider         question            n  accuracy errors   p50 ms   p95 ms
-------------------------------------------------------------------------
keyword          mood                8     50.0%      0      0.1      0.1
keyword          team               10    100.0%      0      0.1      0.1
keyword          urgent              5     80.0%      0      0.1      0.1

$ s1kit calibrate results.jsonl --target 0.95
keyword/mood: confidence >= 0.5761 -> 100.0% precise, answers 25% of cases
keyword/team: confidence >= 0.3333 -> 100.0% precise, answers 100% of cases
keyword/urgent: confidence >= 0.7143 -> 100.0% precise, answers 40% of cases
```

Read it as: trust the baseline on `team`, but send three quarters of `mood`
questions to a stronger model.

The example runs offline: `keyword` is a built-in word-overlap baseline that needs no
API key. Uncomment a real model in the suite to see how far it beats the baseline.

> Status: alpha (0.1.0). The API may change before 1.0.

## Install

```bash
pip install s1kit
```

To work on s1kit itself, clone the repo and run `pip install -e ".[dev]"`.

## Write a suite

```yaml
providers:
  - type: keyword                      # offline baseline
  - name: laya
    base_url: http://localhost:8080    # any /v1/systemone server
    model: laya
  - name: jev
    base_url: https://api.typesafe.ai
    model: jev-latest
    api_key_env: TYPESAFE_API_KEY

questions:
  team:
    type: choice
    instructions: Which team should handle this ticket?
    criteria:
      billing: Charges, invoices, payment methods
      tech: Login problems, bugs, errors

cases:
  - state: "I was charged twice for my order"
    expect: {team: billing}
```

`choice` expects an option name, `score` a level index or label, `noul` true/false.

## Route in production

```python
import yaml
from s1kit import Router
from s1kit.providers import HttpProvider

thresholds = yaml.safe_load(open("thresholds.yaml"))
router = Router(
    [HttpProvider("laya", "http://localhost:8080", "laya"),
     HttpProvider("jev", "https://api.typesafe.ai", "jev-latest", "TYPESAFE_API_KEY")],
    thresholds,
)
result = router.decide(ticket_text, questions)
result.answers, result.provider, result.escalations
```

The last provider always answers, so put your most capable model at the end.

## Commands

| Command | What it does |
|---|---|
| `s1kit test SUITE [--only NAME] [--fail-under 0.9]` | Run the suite, save every decision to `results.jsonl`, print a comparison |
| `s1kit report RESULTS` | Print the comparison again from a results file |
| `s1kit calibrate RESULTS [--target 0.95]` | Write `thresholds.yaml` with one cutoff per provider and question |

## Roadmap

- 0.2: response cache, JSONL decision log for the router
- 0.3: GitHub Action, pytest plugin, TypeScript package, LangChain and n8n integrations
- 1.0: public dataset packs, stable API

## Contributing

New provider configs, integrations, report formats and datasets are all welcome,
and most fit in one evening. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
