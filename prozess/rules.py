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
