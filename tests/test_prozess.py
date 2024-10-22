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


def test_clean_cases_have_no_findings(log):
    findings = rules.check(log)
    dirty = set().union(*ground_truth(log).values())
    assert set(findings[s.CASE]) <= dirty


def test_bottleneck_is_budget_approval_in_research(log):
    top = analysis.bottlenecks(log).iloc[0]
    assert top["department"] == "Forschung"
    assert (top["von"], top["nach"]) == (s.APPROVED_ADMIN, s.APPROVED_BUDGET)
    assert top["faktor"] > 3


def test_variants_cover_all_cases(log):
    var = analysis.variants(log)
    assert var["faelle"].sum() == log[s.CASE].nunique()
    assert var["kumuliert"].iloc[-1] == pytest.approx(1.0)
    assert var["faelle"].is_monotonic_decreasing


def test_waiting_times_are_positive(log):
    assert (analysis.waiting_times(log)["median"] > 0).all()


def test_discovered_model_fits_normal_process(log):
    model = analysis.process_model(log)
    assert model["fitness"] > 0.95
    assert model["precision"] > 0.7
    assert model["start"] == {s.SUBMITTED: log[s.CASE].nunique()}


def test_xes_roundtrip_gives_same_findings(tmp_path, log):
    """Prüft den XES-Pfad, über den auch die BPI-Challenge-Daten eingelesen werden."""
    import pm4py

    small = log[log[s.CASE].isin(log[s.CASE].unique()[:400])].copy()
    xes = small.rename(columns={s.CASE: "case:concept:name", s.ACTIVITY: "concept:name",
                                s.TIMESTAMP: "time:timestamp", s.RESOURCE: "org:resource",
                                "amount": "case:Amount", "department": "case:department"})
    xes["time:timestamp"] = pd.to_datetime(xes["time:timestamp"], utc=True)
    path = tmp_path / "log.xes"
    pm4py.write_xes(xes.drop(columns=["injected"]), str(path))

    loaded = analysis.load_log(path)
    assert len(loaded) == len(small)
    expected = rules.check(small).sort_values([s.CASE, "regel"]).reset_index(drop=True)
    actual = rules.check(loaded).sort_values([s.CASE, "regel"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(expected, actual)
