"""Create the outreach spreadsheet with its two tabs and save SHEET_ID to .env."""

import os

from dotenv import set_key

from outreach.google_client import credentials, sheets_service
from outreach.store import COMPANIES, COMPANY_COLUMNS, CONTACT_COLUMNS, CONTACTS

# Target companies. first_line (the personalized opener) is filled in by hand in the sheet.
STARTING_COMPANIES = [
    ["datadoghq.com", "Datadog", "", "yes"],
    ["doordash.com", "DoorDash", "", "yes"],
    ["plaid.com", "Plaid", "", "yes"],
    ["bloomberg.com", "Bloomberg", "", "yes"],
]

if os.getenv("SHEET_ID"):
    raise SystemExit("SHEET_ID is already set in .env. Clear it first to create a new sheet.")

service = sheets_service(credentials())
spreadsheet = service.spreadsheets().create(
    body={
        "properties": {"title": "Recruiter Outreach"},
        "sheets": [
            {"properties": {"title": COMPANIES, "gridProperties": {"frozenRowCount": 1}}},
            {"properties": {"title": CONTACTS, "gridProperties": {"frozenRowCount": 1}}},
        ],
    }
).execute()
sheet_id = spreadsheet["spreadsheetId"]

service.spreadsheets().values().batchUpdate(
    spreadsheetId=sheet_id,
    body={
        "valueInputOption": "RAW",
        "data": [
            {"range": f"{COMPANIES}!A1", "values": [COMPANY_COLUMNS, *STARTING_COMPANIES]},
            {"range": f"{CONTACTS}!A1", "values": [CONTACT_COLUMNS]},
        ],
    },
).execute()

set_key(".env", "SHEET_ID", sheet_id)
print(f"Created {spreadsheet['spreadsheetUrl']}")
print("Saved SHEET_ID to .env")
