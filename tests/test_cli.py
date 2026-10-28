from pathlib import Path

from s1kit import cli, runner, suite
from s1kit.providers import KeywordProvider

ROOT = Path(__file__).parent.parent


def test_starter_template_is_the_example_suite():
    starter = ROOT / "src" / "s1kit" / "starter.yaml"
    example = ROOT / "examples" / "support-tickets.yaml"
    assert starter.read_text(encoding="utf-8") == example.read_text(encoding="utf-8")


def test_init_then_test_works_with_no_arguments(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["init"]) == 0
    assert (tmp_path / "s1kit.yaml").exists()
    assert cli.main(["test"]) == 0
    out = capsys.readouterr().out
    assert "keyword: 18/23 correct (78.3%)" in out
    assert (tmp_path / "results.jsonl").exists()


def test_init_does_not_overwrite_without_force(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "s1kit.yaml").write_text("mine")
    assert cli.main(["init"]) == 1
    assert (tmp_path / "s1kit.yaml").read_text() == "mine"
    assert cli.main(["init", "--force"]) == 0
    assert "questions:" in (tmp_path / "s1kit.yaml").read_text()


def test_missing_suite_points_to_init(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["test"]) == 2
    assert "s1kit init" in capsys.readouterr().err


def test_fail_under(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli.main(["init"])
    assert cli.main(["test", "--fail-under", "0.7"]) == 0
    assert cli.main(["test", "--fail-under", "0.9"]) == 1


def test_concurrency_keeps_suite_order(tmp_path):
    s = suite.load(ROOT / "examples" / "support-tickets.yaml")
    providers = [KeywordProvider("a"), KeywordProvider("b")]
    serial = runner.run(s, providers)
    parallel = runner.run(s, providers, concurrency=8)
    key = lambda r: (r.provider, r.case, r.question, r.label, r.correct)  # noqa: E731
    assert [key(r) for r in parallel] == [key(r) for r in serial]
