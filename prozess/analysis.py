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


def variants(log: pd.DataFrame) -> pd.DataFrame:
    """Häufigkeit jeder Aktivitätsfolge, mit kumuliertem Anteil."""
    seq = log.groupby(s.CASE, sort=False)[s.ACTIVITY].agg(" → ".join)
    counts = seq.value_counts().rename_axis("variante").reset_index(name="faelle")
    counts["anteil"] = counts["faelle"] / counts["faelle"].sum()
    counts["kumuliert"] = counts["anteil"].cumsum()
    return counts


def case_durations(log: pd.DataFrame, by: str | None = None) -> pd.DataFrame:
    grouped = log.groupby(s.CASE)
    out = pd.DataFrame({"tage": (grouped[s.TIMESTAMP].max() - grouped[s.TIMESTAMP].min()).dt.total_seconds() / 86_400})
    if by and by in log:
        out[by] = grouped[by].first()
    return out


def waiting_times(log: pd.DataFrame, by: str | None = None) -> pd.DataFrame:
    """Wartezeit zwischen zwei aufeinanderfolgenden Aktivitäten eines Falls.

    Der Median ist robuster als der Mittelwert, weil einzelne liegengebliebene
    Anträge den Mittelwert stark verzerren.
    """
    df = log.sort_values([s.CASE, s.TIMESTAMP]).copy()
    df["von"] = df.groupby(s.CASE)[s.ACTIVITY].shift()
    df["stunden"] = df.groupby(s.CASE)[s.TIMESTAMP].diff().dt.total_seconds() / 3600
    df = df.dropna(subset=["von"]).rename(columns={s.ACTIVITY: "nach"})
    keys = ["von", "nach"] + ([by] if by and by in df else [])
    result = df.groupby(keys)["stunden"].agg(anzahl="count", median="median", p90=lambda x: x.quantile(0.9)).reset_index()
    return result.sort_values("median", ascending=False).reset_index(drop=True)


def bottlenecks(log: pd.DataFrame, by: str = "department", min_cases: int = 30) -> pd.DataFrame:
    """Übergänge, die in einer Gruppe deutlich länger dauern als im Rest.

    faktor = Median in der Gruppe / Median in allen anderen Gruppen.
    """
    if by not in log:
        return pd.DataFrame()
    parts = []
    for group, part in log.groupby(by):
        inside = waiting_times(part)
        rest = waiting_times(log[log[by] != group])[["von", "nach", "median"]]
        merged = inside.merge(rest, on=["von", "nach"], suffixes=("", "_rest"))
        merged = merged[merged["anzahl"] >= min_cases].assign(**{by: group})
        parts.append(merged)
    result = pd.concat(parts, ignore_index=True)
    result["faktor"] = result["median"] / result["median_rest"]
    return result.sort_values("faktor", ascending=False).reset_index(drop=True)


def to_pm4py(log: pd.DataFrame) -> pd.DataFrame:
    import pm4py

    return pm4py.format_dataframe(log.copy(), case_id=s.CASE, activity_key=s.ACTIVITY, timestamp_key=s.TIMESTAMP)


def process_model(log: pd.DataFrame, noise: float = 0.2) -> dict:
    """Prozessmodell mit dem Inductive Miner entdecken und bewerten.

    fitness: wie gut das Modell die Fälle im Log abspielen kann (1 = alle)
    precision: wie wenig zusätzliches Verhalten das Modell erlaubt (1 = nichts)
    Der Noise-Schwellwert lässt seltene Pfade (die Verstöße) bewusst weg,
    damit das Modell den Normalprozess zeigt.
    """
    import pm4py

    df = to_pm4py(log)
    net, im, fm = pm4py.discover_petri_net_inductive(df, noise_threshold=noise)
    fitness = pm4py.fitness_token_based_replay(df, net, im, fm)
    precision = pm4py.precision_token_based_replay(df, net, im, fm)
    dfg, starts, ends = pm4py.discover_dfg(df)
    edges = (
        pd.DataFrame([(a, b, n) for (a, b), n in dfg.items()], columns=["von", "nach", "anzahl"])
        .sort_values("anzahl", ascending=False)
        .reset_index(drop=True)
    )
    return {
        "net": (net, im, fm),
        "fitness": float(fitness["log_fitness"]),
        "precision": float(precision),
        "dfg": edges,
        "start": dict(starts),
        "ende": dict(ends),
    }


def save_model_picture(log: pd.DataFrame, path: str | Path, noise: float = 0.2) -> Path:
    """Prozessmodell als BPMN-Bild speichern. Braucht Graphviz (https://graphviz.org)."""
    import pm4py

    tree = pm4py.discover_process_tree_inductive(to_pm4py(log), noise_threshold=noise)
    pm4py.save_vis_bpmn(pm4py.convert_to_bpmn(tree), str(path))
    return Path(path)
