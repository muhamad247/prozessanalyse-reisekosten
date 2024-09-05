from pathlib import Path

import pandas as pd
import pytest

from prozess import analysis, rules
from prozess import schema as s
from prozess.simulate import ground_truth, simulate

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def log():
    return simulate(3000, seed=7)


def test_simulation_is_reproducible():
    a, b = simulate(200, seed=1), simulate(200, seed=1)
    pd.testing.assert_frame_equal(a, b)


def test_every_case_starts_with_submission(log):
    first = log.groupby(s.CASE)[s.ACTIVITY].first()
    assert (first == s.SUBMITTED).all()


@pytest.mark.parametrize("rule_id", list(rules.RULES))
def test_rules_find_exactly_the_injected_cases(log, rule_id):
    """Keine Fehlalarme und nichts übersehen: gefundene Fälle == eingebaute Fälle."""
    truth = ground_truth(log).get(rule_id, set())
    findings = rules.check(log)
    found = set(findings.loc[findings["regel"] == rule_id, s.CASE])
    assert truth, f"Simulator hat keine Fälle für {rule_id} erzeugt"
    assert found == truth
