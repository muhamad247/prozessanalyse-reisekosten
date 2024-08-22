"""Erzeugt ein Reisekosten-Event-Log mit bekannten Mustern.

Warum simuliert? Bei echten Logs weiß niemand, welche Auffälligkeiten
wirklich drinstecken. Hier sind sie absichtlich eingebaut und pro Fall in
der Spalte `injected` vermerkt. Die Tests prüfen, ob die Analyse genau diese
Fälle wiederfindet, nicht mehr und nicht weniger.

Eingebaute Muster:
- Engpass: Budgetverantwortliche in der Abteilung Forschung brauchen deutlich länger
- Nacharbeit: ein Teil der Anträge wird abgelehnt und neu eingereicht
- skip_supervisor: Zahlung ohne finale Freigabe durch Vorgesetzte
- missing_director: Betrag über 5.000 EUR, aber keine Freigabe durch die Direktion
- self_approval: Vorgesetzte genehmigen ihren eigenen Antrag (Vier-Augen-Prinzip verletzt)
- early_payment: Zahlung angefordert, bevor das Budget freigegeben ist
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from . import schema as s

DEPARTMENTS = ["Verwaltung", "Forschung", "Lehre", "IT"]


def _hours(rng: np.random.Generator, median: float) -> timedelta:
    """Lognormal verteilte Dauer mit gegebenem Median (in Stunden)."""
    return timedelta(hours=float(rng.lognormal(np.log(median), 0.6)))


def simulate(n_cases: int = 3000, seed: int = 7, start: str = "2025-01-01") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t0 = datetime.fromisoformat(start)
    staff = {d: {"budget": f"budget_{d[:3].lower()}", "supervisor": f"chef_{d[:3].lower()}"} for d in DEPARTMENTS}
    admins = ["admin_1", "admin_2", "admin_3"]
    rows = []

    for i in range(n_cases):
        case = f"D{i + 1:05d}"
        dept = DEPARTMENTS[rng.choice(4, p=[0.3, 0.3, 0.25, 0.15])]
        amount = round(float(rng.lognormal(np.log(450), 1.0)), 2)
        employee = f"emp_{rng.integers(1, 400):03d}"
        injected = []

        # Seltene Muster schließen sich gegenseitig aus, damit jeder Fall genau eine Ursache hat
        u = rng.random()
        if amount > s.DIRECTOR_THRESHOLD and u < 0.4:
            injected.append("missing_director")
        elif u < 0.02:
            injected.append("skip_supervisor")
        elif u < 0.03:
            injected.append("self_approval")
            employee = staff[dept]["supervisor"]  # Vorgesetzte reicht selbst ein ...
        elif u < 0.04:
            injected.append("early_payment")

        t = t0 + timedelta(days=float(rng.uniform(0, 365)))
        events = []

        def add(activity: str, resource: str, wait_median_h: float) -> None:
            nonlocal t
            t = t + _hours(rng, wait_median_h)
            events.append((activity, t, resource))

        add(s.SUBMITTED, employee, 0.1)

        # Nacharbeit: Ablehnung durch die Verwaltung, dann neue Einreichung
        while rng.random() < 0.08:
            add(s.REJECTED_ADMIN, rng.choice(admins), 20)
            add(s.SUBMITTED, employee, 30)
        add(s.APPROVED_ADMIN, rng.choice(admins), 20)

        if "early_payment" in injected:
            add(s.REQUEST_PAYMENT, "SYSTEM", 2)

        budget_wait = 120 if dept == "Forschung" else 24  # Engpass
        add(s.APPROVED_BUDGET, staff[dept]["budget"], budget_wait)

        if not injected and rng.random() < 0.02:  # endgültig abgelehnt, keine Zahlung
            add(s.REJECTED_SUPERVISOR, staff[dept]["supervisor"], 24)
            rows += [(case, a, ts, r, dept, amount, ",".join(injected)) for a, ts, r in events]
            continue

        if "skip_supervisor" not in injected:
            add(s.FINAL_SUPERVISOR, staff[dept]["supervisor"], 24)
        if amount > s.DIRECTOR_THRESHOLD and "missing_director" not in injected:
            add(s.FINAL_DIRECTOR, "direktion", 48)
        if "early_payment" not in injected:
            add(s.REQUEST_PAYMENT, "SYSTEM", 2)
        add(s.PAYMENT_HANDLED, "SYSTEM", 72)

        rows += [(case, a, ts, r, dept, amount, ",".join(injected)) for a, ts, r in events]

    df = pd.DataFrame(rows, columns=[s.CASE, s.ACTIVITY, s.TIMESTAMP, s.RESOURCE, "department", "amount", "injected"])
    return df.sort_values([s.CASE, s.TIMESTAMP]).reset_index(drop=True)


def ground_truth(df: pd.DataFrame) -> dict[str, set[str]]:
    """Fall-IDs je eingebautem Muster, zum Vergleich mit den Analyseergebnissen."""
    cases = df.groupby(s.CASE)["injected"].first()
    truth: dict[str, set[str]] = {}
    for case, labels in cases.items():
        for label in filter(None, labels.split(",")):
            truth.setdefault(label, set()).add(case)
    return truth
