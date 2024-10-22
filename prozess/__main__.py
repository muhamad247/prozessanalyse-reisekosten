"""Kommandozeile.

  python -m prozess simulieren --faelle 3000 --datei data/reisekosten.csv
  python -m prozess analysieren data/reisekosten.csv
  python -m prozess analysieren DomesticDeclarations.xes.gz     (BPI Challenge 2020)
"""

import argparse
import sys

import pandas as pd

from . import analysis, rules
from .simulate import simulate


def cmd_simulate(args) -> int:
    log = simulate(args.faelle, seed=args.seed)
    log.to_csv(args.datei, index=False)
    print(f"{log['case_id'].nunique()} Fälle, {len(log)} Ereignisse → {args.datei}")
    return 0


def cmd_analyse(args) -> int:
    log = analysis.load_log(args.datei)
    pd.set_option("display.width", 160, "display.max_colwidth", 60)

    print("Überblick")
    for key, value in analysis.summary(log).items():
        print(f"  {key}: {value}")

    print("\nHäufigste Varianten")
    print(analysis.variants(log).head(5)[["faelle", "anteil", "variante"]].to_string(index=False))

    print("\nLängste Wartezeiten (Median, Stunden)")
    print(analysis.waiting_times(log).head(5)[["von", "nach", "anzahl", "median"]].round(1).to_string(index=False))

    found = analysis.bottlenecks(log)
    if not found.empty:
        top = found.iloc[0]
        print(f"\nAuffälligster Engpass: {top['department']}, {top['von']} → {top['nach']}: "
              f"Median {top['median']:.0f} h statt {top['median_rest']:.0f} h ({top['faktor']:.1f}-fach)")

    findings = rules.check(log)
    print(f"\nRegelverstöße: {len(findings)} in {findings['case_id'].nunique()} Fällen")
    if not findings.empty:
        print(findings.groupby("titel").size().to_string())

    model = analysis.process_model(log)
    print(f"\nProzessmodell (Inductive Miner): Fitness {model['fitness']:.3f}, Precision {model['precision']:.3f}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m prozess")
    sub = parser.add_subparsers(dest="befehl", required=True)

    p = sub.add_parser("simulieren", help="Event-Log mit bekannten Mustern erzeugen")
    p.add_argument("--faelle", type=int, default=3000)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--datei", default="data/reisekosten.csv")
    p.set_defaults(func=cmd_simulate)

    p = sub.add_parser("analysieren", help="Log auswerten (CSV oder XES)")
    p.add_argument("datei")
    p.set_defaults(func=cmd_analyse)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
