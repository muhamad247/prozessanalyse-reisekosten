"""Process-Mining-Auswertungen: Varianten, Durchlaufzeiten, Wartezeiten, Prozessmodell."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import schema as s


def load_log(path: str | Path) -> pd.DataFrame:
    """Liest CSV (internes Format) oder XES (z. B. BPI Challenge 2020)."""
    path = Path(path)
    if path.suffix == ".csv":
        df = pd.read_csv(path, parse_dates=[s.TIMESTAMP])
    else:
        import pm4py  # nur für XES nötig, lädt relativ langsam

        df = pm4py.read_xes(str(path))
        df = df.rename(columns={k: v for k, v in s.XES_COLUMNS.items() if k in df.columns})
    df[s.TIMESTAMP] = pd.to_datetime(df[s.TIMESTAMP], utc=True)
    if s.RESOURCE not in df:
        df[s.RESOURCE] = "unbekannt"
    df[s.CASE] = df[s.CASE].astype(str)
    return df.sort_values([s.CASE, s.TIMESTAMP]).reset_index(drop=True)


def summary(log: pd.DataFrame) -> dict[str, float]:
    durations = case_durations(log)
    return {
        "Fälle": log[s.CASE].nunique(),
        "Ereignisse": len(log),
        "Aktivitäten": log[s.ACTIVITY].nunique(),
        "Varianten": len(variants(log)),
        "Median Durchlaufzeit (Tage)": round(float(durations["tage"].median()), 1),
    }
