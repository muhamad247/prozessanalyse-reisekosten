"""Streamlit-Oberfläche: streamlit run app.py"""

import tempfile
from pathlib import Path

import streamlit as st

from prozess import analysis, rules
from prozess.simulate import ground_truth, simulate

st.set_page_config(page_title="Prozessanalyse Reisekosten", layout="wide")
st.title("Process Mining: Reisekostenanträge")

with st.sidebar:
    source = st.radio("Daten", ["Simuliertes Log", "Eigene Datei (CSV oder XES)"])
    if source == "Simuliertes Log":
        n = st.slider("Fälle", 500, 10_000, 3000, step=500)
        seed = st.number_input("Seed", 0, 10_000, 7)
        log = simulate(n, seed=int(seed))
    else:
        upload = st.file_uploader("Event-Log", type=["csv", "xes", "gz"])
        if upload is None:
            st.info("Z. B. DomesticDeclarations.xes.gz aus der BPI Challenge 2020")
            st.stop()
        suffix = ".csv" if upload.name.endswith(".csv") else ".xes.gz" if upload.name.endswith(".gz") else ".xes"
        path = Path(tempfile.mkdtemp()) / f"log{suffix}"
        path.write_bytes(upload.getvalue())
        log = analysis.load_log(path)

cols = st.columns(5)
for col, (label, value) in zip(cols, analysis.summary(log).items()):
    col.metric(label, value)

tab_var, tab_wait, tab_rules, tab_model = st.tabs(["Varianten", "Engpässe", "Regelverstöße", "Prozessmodell"])

with tab_var:
    var = analysis.variants(log)
    st.caption(f"Die häufigste Variante deckt {var['anteil'].iloc[0]:.0%} der Fälle ab, die Top 3 {var['kumuliert'].iloc[min(2, len(var) - 1)]:.0%}.")
    st.dataframe(var.head(15).round(3), hide_index=True)

with tab_wait:
    st.subheader("Wartezeiten zwischen Schritten (Stunden)")
    st.dataframe(analysis.waiting_times(log).round(1), hide_index=True)
    found = analysis.bottlenecks(log)
    if not found.empty:
        top = found.iloc[0]
        st.warning(f"**{top['department']}**: {top['von']} → {top['nach']} dauert im Median "
                   f"{top['median']:.0f} h, in den anderen Abteilungen {top['median_rest']:.0f} h "
                   f"({top['faktor']:.1f}-fach).")
        st.dataframe(found.head(10).round(2), hide_index=True)
    durations = analysis.case_durations(log, by="department")
    if "department" in durations:
        st.subheader("Durchlaufzeit pro Abteilung (Tage, Median)")
        st.bar_chart(durations.groupby("department")["tage"].median())

with tab_rules:
    findings = rules.check(log)
    st.write(f"**{len(findings)} Verstöße** in {findings['case_id'].nunique()} von {log['case_id'].nunique()} Fällen")
    if not findings.empty:
        st.bar_chart(findings["titel"].value_counts())
        st.dataframe(findings, hide_index=True)
    if "injected" in log:
        truth = ground_truth(log)
        hits = {r: set(findings.loc[findings["regel"] == r, "case_id"]) for r in rules.RULES}
        ok = all(hits[r] == truth.get(r, set()) for r in rules.RULES)
        st.caption("Abgleich mit den im Simulator eingebauten Fällen: "
                   + ("alle gefunden, keine Fehlalarme." if ok else "Abweichung, siehe Tests."))

with tab_model:
    model = analysis.process_model(log)
    c1, c2 = st.columns(2)
    c1.metric("Fitness", f"{model['fitness']:.3f}")
    c2.metric("Precision", f"{model['precision']:.3f}")
    st.caption("Inductive Miner mit Noise-Schwelle 0,2: Seltene Pfade (z. B. die Verstöße) bleiben bewusst draußen, "
               "das Modell zeigt den Normalprozess.")
    st.subheader("Übergänge (Directly-Follows-Graph)")
    st.dataframe(model["dfg"], hide_index=True)
