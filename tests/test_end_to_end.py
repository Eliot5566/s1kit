from pathlib import Path

from s1kit import cli, runner

EXAMPLE = Path(__file__).parent.parent / "examples" / "support-tickets.yaml"


def test_example_suite_runs_offline_and_calibrates(tmp_path, capsys):
    results = tmp_path / "results.jsonl"
    thresholds = tmp_path / "thresholds.yaml"
    assert cli.main(["test", str(EXAMPLE), "--out", str(results)]) == 0
    records = runner.load(results)
    assert records and all(r.provider == "keyword" and r.error is None for r in records)
    assert cli.main(["calibrate", str(results), "--target", "0.8", "--out", str(thresholds)]) == 0
    assert "target_precision: 0.8" in thresholds.read_text()
    assert "keyword" in capsys.readouterr().out


def test_unknown_provider_filter_is_an_error(tmp_path):
    out = tmp_path / "results.jsonl"
    assert cli.main(["test", str(EXAMPLE), "--only", "nope", "--out", str(out)]) == 2
    assert not out.exists()
