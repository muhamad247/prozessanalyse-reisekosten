# Daten

`python -m prozess simulieren` legt hier `reisekosten.csv` an (wird nicht eingecheckt).

## Echte Daten: BPI Challenge 2020

Reisekostenabrechnungen einer niederländischen Universität, frei verfügbar bei 4TU.ResearchData
(Suche nach "BPI Challenge 2020"), z. B. `DomesticDeclarations.xes.gz` oder `PermitLog.xes.gz`.

```bash
python -m prozess analysieren DomesticDeclarations.xes.gz
```

Die Dateien bitte nicht ins Repository legen und die Lizenz auf der 4TU-Seite beachten.
Weichen die Aktivitätsnamen von denen in `prozess/schema.py` ab, dort anpassen.
Ohne Betrag oder Abteilung im Log fallen die Direktionsregel und die Engpassanalyse nach Abteilung weg,
der Rest funktioniert mit jedem Log aus Fall-ID, Aktivität und Zeitstempel.
