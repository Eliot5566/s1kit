"""s1kit command line: init, test, report, calibrate."""

import argparse
import os
import sys
from importlib.resources import files

import yaml

from . import __version__, calibrate, report, runner, suite

DEFAULT_SUITE = "s1kit.yaml"


def cmd_init(args):
    if os.path.exists(args.path) and not args.force:
        print(f"{args.path} already exists; pass --force to overwrite it", file=sys.stderr)
        return 1
    with open(args.path, "w", encoding="utf-8") as fh:
        fh.write(files("s1kit").joinpath("starter.yaml").read_text(encoding="utf-8"))
    run = "s1kit test" if args.path == DEFAULT_SUITE else f"s1kit test {args.path}"
    edit = f"edit {args.path}"
    width = max(len(run), len(edit)) + 3
    print(f"wrote {args.path}: 10 support tickets, 3 questions, an offline baseline\n\nnext:\n"
          f"  {run:<{width}}# try it, no model or API key needed\n"
          f"  {edit:<{width}}# uncomment a real model, add your own cases")
    return 0


def cmd_test(args):
    if not os.path.exists(args.suite):
        hint = "; run `s1kit init` to create one" if args.suite == DEFAULT_SUITE else ""
        print(f"no suite at {args.suite}{hint}", file=sys.stderr)
        return 2
    s = suite.load(args.suite)
    providers = [p for p in s.providers if not args.only or p.name in args.only]
    if not providers:
        print(f"no provider named {', '.join(args.only)} in {args.suite}", file=sys.stderr)
        return 2
    records = runner.run(s, providers, concurrency=args.concurrency)
    runner.save(records, args.out)
    print(report.render(report.summarize(records)))
    print(f"\n{report.overall(records)}\n{len(records)} decisions saved to {args.out}")
    if args.fail_under is not None and records:
        accuracy = sum(r.correct for r in records) / len(records)
        if accuracy < args.fail_under:
            print(f"accuracy {accuracy:.1%} is below --fail-under {args.fail_under:.1%}")
            return 1
    return 0


def cmd_report(args):
    records = runner.load(args.results)
    print(report.render(report.summarize(records)))
    print(f"\n{report.overall(records)}")
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

    init = sub.add_parser("init", help="write a starter suite you can run right away")
    init.add_argument("path", nargs="?", default=DEFAULT_SUITE, help=f"where to write it (default {DEFAULT_SUITE})")
    init.add_argument("--force", action="store_true", help="overwrite an existing file")
    init.set_defaults(func=cmd_init)

    test = sub.add_parser("test", help="run a suite against its providers")
    test.add_argument("suite", nargs="?", default=DEFAULT_SUITE, help=f"suite YAML file (default {DEFAULT_SUITE})")
    test.add_argument("--out", default="results.jsonl", help="where to save decisions (default results.jsonl)")
    test.add_argument("--only", action="append", help="run only this provider (repeatable)")
    test.add_argument("-j", "--concurrency", type=int, default=1, metavar="N",
                      help="requests in flight at once (default 1)")
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
