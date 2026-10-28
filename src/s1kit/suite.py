"""Load a test suite: providers, questions and cases with expected answers."""

from dataclasses import dataclass, field

import yaml

from .providers import from_config


@dataclass
class Case:
    state: object
    expect: dict
    id: str = ""


@dataclass
class Suite:
    questions: dict
    cases: list
    providers: list = field(default_factory=list)


def load(path):
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    questions = raw["questions"]
    cases = []
    for i, c in enumerate(raw["cases"], 1):
        unknown = set(c["expect"]) - set(questions)
        if unknown:
            raise ValueError(f"case {i} expects unknown question(s): {sorted(unknown)}")
        cases.append(Case(state=c["state"], expect=c["expect"], id=str(c.get("id", i))))
    providers = [from_config(p) for p in raw.get("providers", [{"type": "keyword"}])]
    return Suite(questions=questions, cases=cases, providers=providers)
