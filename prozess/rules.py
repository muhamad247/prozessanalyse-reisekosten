"""Compliance-Regeln für Reisekostenanträge.

Jede Regel bekommt einen Fall (Aktivitäten und Ressourcen in zeitlicher
Reihenfolge) und liefert eine Begründung, wenn sie verletzt ist, sonst None.
Regelbasiert statt über ein Petri-Netz, weil sich so jede Abweichung in einem
Satz erklären lässt, und genau das braucht eine Revision oder das Controlling.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from . import schema as s


@dataclass(frozen=True)
class Case:
    id: str
    activities: list[str]
    resources: list[str]
    amount: float | None

    def first(self, activity: str) -> int | None:
        return self.activities.index(activity) if activity in self.activities else None


Rule = Callable[[Case], str | None]


def payment_without_final_approval(case: Case) -> str | None:
    paid = case.first(s.PAYMENT_HANDLED)
    if paid is None:
        return None
    approved = case.first(s.FINAL_SUPERVISOR)
    if approved is None or approved > paid:
        return "Zahlung ohne finale Freigabe durch Vorgesetzte"
    return None


def missing_director_approval(case: Case) -> str | None:
    if case.amount is None or case.amount <= s.DIRECTOR_THRESHOLD or case.first(s.PAYMENT_HANDLED) is None:
        return None
    if case.first(s.FINAL_DIRECTOR) is None:
        return f"{case.amount:,.2f} EUR ausgezahlt ohne Freigabe der Direktion (Grenze {s.DIRECTOR_THRESHOLD:,} EUR)"
    return None


def four_eyes(case: Case) -> str | None:
    submitters = {r for a, r in zip(case.activities, case.resources) if a == s.SUBMITTED}
    approvers = {r for a, r in zip(case.activities, case.resources) if a in s.APPROVALS}
    same = sorted(submitters & approvers)
    if same:
        return f"Vier-Augen-Prinzip verletzt: {same[0]} hat den eigenen Antrag freigegeben"
    return None


def payment_requested_before_budget(case: Case) -> str | None:
    requested = case.first(s.REQUEST_PAYMENT)
    if requested is None:
        return None
    budget = case.first(s.APPROVED_BUDGET)
    if budget is None or budget > requested:
        return "Zahlung angefordert, bevor das Budget freigegeben war"
    return None


RULES: dict[str, Rule] = {
    "skip_supervisor": payment_without_final_approval,
    "missing_director": missing_director_approval,
    "self_approval": four_eyes,
    "early_payment": payment_requested_before_budget,
}

RULE_TITLES = {
    "skip_supervisor": "Zahlung ohne finale Freigabe",
    "missing_director": "Direktion fehlt ab 5.000 EUR",
    "self_approval": "Vier-Augen-Prinzip",
    "early_payment": "Zahlung vor Budgetfreigabe",
}


def cases(log: pd.DataFrame) -> list[Case]:
    ordered = log.sort_values([s.CASE, s.TIMESTAMP])
    agg = {s.ACTIVITY: list, s.RESOURCE: list}
    if "amount" in ordered:
        agg["amount"] = "first"
    grouped = ordered.groupby(s.CASE, sort=False).agg(agg)
    return [
        Case(str(cid), row[s.ACTIVITY], [str(r) for r in row[s.RESOURCE]],
             None if "amount" not in row or pd.isna(row["amount"]) else float(row["amount"]))
        for cid, row in grouped.iterrows()
    ]


def check(log: pd.DataFrame) -> pd.DataFrame:
    """Alle Regeln auf alle Fälle anwenden. Eine Zeile pro Verstoß."""
    findings = [
        {s.CASE: case.id, "regel": rule_id, "titel": RULE_TITLES[rule_id], "begruendung": reason}
        for case in cases(log)
        for rule_id, rule in RULES.items()
        if (reason := rule(case))
    ]
    return pd.DataFrame(findings, columns=[s.CASE, "regel", "titel", "begruendung"])
