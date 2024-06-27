"""Aktivitätsnamen und Spalten an einer Stelle.

Die Namen sind an die Reisekosten-Logs der BPI Challenge 2020 angelehnt
(Domestic Declarations / Travel Permits einer Universität). Weichen sie in
einer anderen Datei ab, reicht es, sie hier anzupassen.
"""

SUBMITTED = "Declaration SUBMITTED by EMPLOYEE"
APPROVED_ADMIN = "Declaration APPROVED by ADMINISTRATION"
APPROVED_BUDGET = "Declaration APPROVED by BUDGET OWNER"
FINAL_SUPERVISOR = "Declaration FINAL_APPROVED by SUPERVISOR"
FINAL_DIRECTOR = "Declaration FINAL_APPROVED by DIRECTOR"
REJECTED_ADMIN = "Declaration REJECTED by ADMINISTRATION"
REJECTED_SUPERVISOR = "Declaration REJECTED by SUPERVISOR"
REQUEST_PAYMENT = "Request Payment"
PAYMENT_HANDLED = "Payment Handled"

APPROVALS = (APPROVED_ADMIN, APPROVED_BUDGET, FINAL_SUPERVISOR, FINAL_DIRECTOR)

# Ab diesem Betrag (EUR) muss zusätzlich die Direktion freigeben
DIRECTOR_THRESHOLD = 5_000

# Spalten im internen Format (eine Zeile pro Ereignis)
CASE, ACTIVITY, TIMESTAMP, RESOURCE = "case_id", "activity", "timestamp", "resource"

# Zuordnung der Standard-XES-Schlüssel auf das interne Format
XES_COLUMNS = {
    "case:concept:name": CASE,
    "concept:name": ACTIVITY,
    "time:timestamp": TIMESTAMP,
    "org:resource": RESOURCE,
    "case:Amount": "amount",
    "case:department": "department",
}
