"""s1kit command line: test, report, calibrate."""

import argparse
import sys

import yaml

from . import __version__, calibrate, report, runner, suite


def cmd_test(args):
    s = suite.load(args.suite)
    providers = [p for p in s.providers if not args.only or p.name in args.only]
    if not providers:
        print(f"no provider named {', '.join(args.only)} in {args.suite}", file=sys.stderr)
        return 2
    records = runner.run(s, providers)
    runner.save(records, args.out)
    print(report.render(report.summarize(records)))
    print(f"\n{len(records)} decisions saved to {args.out}")
    if args.fail_under is not None and records:
        accuracy = sum(r.correct for r in records) / len(records)
        if accuracy < args.fail_under:
            print(f"accuracy {accuracy:.1%} is below --fail-under {args.fail_under:.1%}")
            return 1
    return 0


def cmd_report(args):
    print(report.render(report.summarize(runner.load(args.results))))
    return 0


def cmd_calibrate(args):
    result = calibrate.calibrate(runner.load(args.results), args.target)
    with open(args.out, "w", encoding="utf-8") as fh:
        yaml.safe_dump(result, fh, sort_keys=False, allow_unicode=True)
    for provider, questions in result["providers"].items():
        for question, cut in questions.items():
            if cut is None:
                print(f"{provider}/{question}: no cutoff reaches {args.target:.0%}, always escalate")
            else:
                print(f"{provider}/{question}: confidence >= {cut['threshold']} -> "
                      f"{cut['precision']:.1%} precise, answers {cut['coverage']:.0%} of cases")
    print(f"\nthresholds written to {args.out}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="s1kit", description="Test, calibrate and route System One decision models.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    test = sub.add_parser("test", help="run a suite against its providers")
    test.add_argument("suite", help="suite YAML file")
    test.add_argument("--out", default="results.jsonl", help="where to save decisions (default results.jsonl)")
    test.add_argument("--only", action="append", help="run only this provider (repeatable)")
    test.add_argument("--fail-under", type=float, help="exit 1 if overall accuracy is below this, e.g. 0.9")
    test.set_defaults(func=cmd_test)

    rep = sub.add_parser("report", help="summarize a results file")
    rep.add_argument("results")
    rep.set_defaults(func=cmd_report)

    cal = sub.add_parser("calibrate", help="pick confidence cutoffs from a results file")
    cal.add_argument("results")
    cal.add_argument("--target", type=float, default=0.95, help="precision to reach (default 0.95)")
    cal.add_argument("--out", default="thresholds.yaml")
    cal.set_defaults(func=cmd_calibrate)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
