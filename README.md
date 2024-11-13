# Process Mining: Reisekostenanträge

Wo bleiben Reisekostenanträge liegen, und wo wird am Freigabeprozess vorbei bezahlt? Das Projekt wertet Event-Logs mit [pm4py](https://processintelligence.solutions/pm4py) aus: Prozessvarianten, Wartezeiten zwischen den Schritten, Engpässe pro Abteilung, ein automatisch entdecktes Prozessmodell und Compliance-Regeln wie das Vier-Augen-Prinzip.

## Warum ein simuliertes Log?

Bei echten Daten weiß niemand, welche Auffälligkeiten wirklich drinstecken. Ob eine Analyse funktioniert, lässt sich dort kaum prüfen. Der Simulator baut deshalb gezielt Muster ein und merkt sich pro Fall, was er eingebaut hat:

| Muster | eingebaut als |
|---|---|
| Engpass | Budgetfreigabe in der Abteilung Forschung dauert ca. 5-mal so lang |
| Nacharbeit | 8 % der Anträge werden abgelehnt und neu eingereicht |
| Zahlung ohne finale Freigabe | Freigabe durch Vorgesetzte fehlt |
| Direktion fehlt | über 5.000 EUR ausgezahlt ohne Direktionsfreigabe |
| Vier-Augen-Prinzip | Vorgesetzte genehmigen den eigenen Antrag |
| Zahlung vor Budgetfreigabe | Reihenfolge vertauscht |

Die Tests prüfen, dass die Analyse **genau diese Fälle** findet: keine übersehen, keine Fehlalarme.

Für echte Daten liest das Projekt XES-Dateien, z. B. die Reisekosten-Logs der BPI Challenge 2020 (siehe `data/README.md`). Die Aktivitätsnamen des Simulators sind daran angelehnt.

## Ergebnis auf dem simulierten Log (3.000 Fälle)

```
Auffälligster Engpass: Forschung, Declaration APPROVED by ADMINISTRATION
  → Declaration APPROVED by BUDGET OWNER: Median 115 h statt 23 h (4.9-fach)

Regelverstöße: 127 in 127 Fällen
  Direktion fehlt ab 5.000 EUR     6
  Vier-Augen-Prinzip              35
  Zahlung ohne finale Freigabe    59
  Zahlung vor Budgetfreigabe      27

Prozessmodell (Inductive Miner): Fitness 0.995, Precision 0.886
```

88 % der Fälle laufen über genau einen Pfad. Die zweithäufigste Variante (7 %) ist die Nacharbeitsschleife über eine Ablehnung.

## Starten

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt

python -m prozess simulieren                          # data/reisekosten.csv erzeugen
python -m prozess analysieren data/reisekosten.csv    # Bericht in der Konsole
python -m prozess analysieren DomesticDeclarations.xes.gz
streamlit run app.py                                  # Oberfläche
pytest
```

## Methoden

**Varianten**: Jeder Fall wird zu seiner Aktivitätsfolge zusammengefasst, dann wird gezählt. Das zeigt schnell, wie viel vom Prozess Standard ist und wie viel Ausnahme.

**Wartezeiten und Engpässe**: Für jedes Paar aufeinanderfolgender Schritte wird die Zeit dazwischen gemessen. Verglichen wird mit dem Median, nicht dem Mittelwert, weil einzelne liegengebliebene Anträge den Mittelwert verzerren. Ein Engpass ist ein Übergang, der in einer Abteilung deutlich länger dauert als in allen anderen (`faktor` = Median in der Abteilung / Median im Rest).

**Prozessmodell**: Der Inductive Miner entdeckt aus dem Log ein Petri-Netz. Die Noise-Schwelle von 0,2 lässt seltene Pfade weg, damit das Modell den Normalprozess zeigt und nicht jede Abweichung als erlaubt einbaut. Bewertet wird mit Token-Based Replay:
- *Fitness*: wie gut das Modell die Fälle im Log abspielen kann
- *Precision*: wie wenig Verhalten das Modell erlaubt, das im Log nie vorkommt

**Compliance-Regeln** (`prozess/rules.py`): bewusst als einfache Regeln statt als Abgleich mit einem Petri-Netz. So lässt sich jeder Verstoß in einem Satz begründen („chef_it hat den eigenen Antrag freigegeben“), und das braucht eine Revision oder das Controlling.

## Projektstruktur

```
prozess/
  schema.py     Aktivitätsnamen, Spalten, Schwellwerte
  simulate.py   Log-Generator mit eingebauten Mustern
  analysis.py   Varianten, Wartezeiten, Engpässe, Prozessmodell (pm4py), XES/CSV laden
  rules.py      Compliance-Regeln
app.py          Streamlit-Oberfläche
tests/          pytest, inkl. XES-Hin-und-Rückweg
```

## Lizenzhinweis

pm4py steht unter AGPL v3. Für ein öffentliches Portfolio-Repository ist das unproblematisch. Wer den Code in einer kommerziellen, nicht offenen Anwendung nutzen will, braucht eine kommerzielle pm4py-Lizenz.
