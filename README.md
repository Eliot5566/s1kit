# s1kit

[![PyPI](https://img.shields.io/pypi/v/s1kit)](https://pypi.org/project/s1kit/)
[![CI](https://github.com/Eliot5566/s1kit/actions/workflows/ci.yml/badge.svg)](https://github.com/Eliot5566/s1kit/actions/workflows/ci.yml)
[![Python](https://img.shields.io/pypi/pyversions/s1kit)](https://pypi.org/project/s1kit/)

**Test, calibrate and route System One decision models on your own data.**

[繁體中文說明](README.zh-TW.md)

## Why

Decision models (Jev, Laya, kev, and anything served by llama.cpp or Ollama) all
speak the same `/v1/systemone` API: you send a state and typed questions, they
send back a choice, a score or a yes/no with a confidence. Swapping models is a
one-line change. Knowing whether you _should_ is not. On day one you need to know:

1. **Which model is most accurate on _my_ data?** `s1kit test` runs one suite against every model side by side.
2. **What confidence can I trust?** `s1kit calibrate` picks a cutoff per question that reaches your target precision.
3. **What happens below that cutoff?** `s1kit.Router` asks the cheapest model first and escalates only when it is unsure.
4. **Did my last change make it worse?** The GitHub Action fails the build when accuracy drops.

## Quickstart

```bash
pip install s1kit
s1kit init      # writes s1kit.yaml: 10 support tickets, 3 questions
s1kit test
```

```
provider         question            n  accuracy errors   p50 ms   p95 ms
-------------------------------------------------------------------------
keyword          mood                8     50.0%      0      0.1      0.2
keyword          team               10    100.0%      0      0.1      0.2
keyword          urgent              5     80.0%      0      0.0      0.2

keyword: 18/23 correct (78.3%)
23 decisions saved to results.jsonl
```

That runs offline: `keyword` is a built-in word-overlap baseline that needs no
model or API key, and it is the bar a real model has to beat. Uncomment a real
model in `s1kit.yaml` to compare it. Then pick confidence cutoffs:

```
$ s1kit calibrate results.jsonl --target 0.95
keyword/mood: confidence >= 0.5761 -> 100.0% precise, answers 25% of cases
keyword/team: confidence >= 0.3333 -> 100.0% precise, answers 100% of cases
keyword/urgent: confidence >= 0.7143 -> 100.0% precise, answers 40% of cases
```

Read it as: trust the baseline on `team`, but send three quarters of `mood`
questions to a stronger model.

## Write a suite

```yaml
providers:
  - type: keyword                      # offline baseline
  - name: laya
    base_url: http://localhost:8000    # laya-serve, or any /v1/systemone server
    model: laya
    timeout: 120                       # seconds; the first request loads the model
  - name: jev
    base_url: https://api.typesafe.ai
    model: jev-latest
    api_key_env: TYPESAFE_API_KEY      # sent as a Bearer token, read from the environment

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
A case only needs to expect the questions you care about.

HTTP providers retry rate limits (429), server errors (5xx) and dropped
connections twice with backoff (set `retries:` to change it). A server that is
down fails at once with `cannot reach ... is the server running?` instead of
stalling the run. Use `s1kit test -j 8` to send eight requests at a time.

## Check accuracy in CI

```yaml
# .github/workflows/s1kit.yml
on: pull_request
jobs:
  s1kit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Eliot5566/s1kit@v0.2.0
        with:
          suite: s1kit.yaml
          fail-under: "0.9"     # fail the job below 90% accuracy
        env:
          TYPESAFE_API_KEY: ${{ secrets.TYPESAFE_API_KEY }}
```

The table lands in the job summary. Inputs: `suite`, `fail-under`, `only`,
`concurrency`, `results`, `python-version`.

## Route in production

```python
import yaml
from s1kit import Router
from s1kit.providers import HttpProvider

thresholds = yaml.safe_load(open("thresholds.yaml"))
router = Router(
    [HttpProvider("laya", "http://localhost:8000", "laya"),
     HttpProvider("jev", "https://api.typesafe.ai", "jev-latest", "TYPESAFE_API_KEY")],
    thresholds,
)
result = router.decide(ticket_text, questions)
result.answers, result.provider, result.escalations
```

The last provider always answers, so put your most capable model at the end.
If a provider fails, the router moves on to the next one.

## Commands

| Command | What it does |
|---|---|
| `s1kit init [PATH]` | Write a starter suite (default `s1kit.yaml`) you can run right away |
| `s1kit test [SUITE] [--only NAME] [-j N] [--fail-under 0.9]` | Run the suite, save every decision to `results.jsonl`, print a comparison |
| `s1kit report RESULTS` | Print the comparison again from a results file |
| `s1kit calibrate RESULTS [--target 0.95]` | Write `thresholds.yaml` with one cutoff per provider and question |

## Compatibility

The HTTP provider is tested against a local server that answers exactly like
laya-serve 0.4 (including its strict Jev mode and `x_jev_confidence`). It has not
yet been run against every hosted model; if a server's answers do not parse,
please [open an issue](https://github.com/Eliot5566/s1kit/issues) with a sample response.

> Status: alpha (0.2.0). The API may change before 1.0.

## Roadmap

- Markdown and JUnit reports, so results show up in pull requests ([#3](https://github.com/Eliot5566/s1kit/issues/3), [#4](https://github.com/Eliot5566/s1kit/issues/4))
- Response cache, so reruns cost nothing ([#8](https://github.com/Eliot5566/s1kit/issues/8))
- Recipes for more servers and ready-made suites for real tasks ([#5](https://github.com/Eliot5566/s1kit/issues/5), [#6](https://github.com/Eliot5566/s1kit/issues/6))
- pytest plugin, TypeScript package, LangChain and n8n integrations
- 1.0: public dataset packs, stable API

## Contributing

New provider recipes, integrations, report formats and datasets are all welcome,
and most fit in one evening. Issues labelled
[good first issue](https://github.com/Eliot5566/s1kit/labels/good%20first%20issue)
are a good place to start. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
