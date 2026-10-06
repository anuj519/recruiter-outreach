"""Google Sheets storage. One spreadsheet, two tabs: Companies and Contacts.

Contact status flow:
  new -> (you set) approved -> contacted -> replied | opted_out | bounced | done
  unverified: enriched but email not verified; kept so credits aren't spent on them again
  skip: set by you to never contact
"""

from datetime import datetime, timezone

COMPANIES = "Companies"
CONTACTS = "Contacts"

COMPANY_COLUMNS = ["domain", "company", "first_line", "active"]
CONTACT_COLUMNS = [
    "company", "domain", "first_name", "last_name", "title", "email", "email_status",
    "linkedin_url", "apollo_id", "status", "added_at", "last_contacted",
    "follow_up_count", "thread_id", "subject", "notes",
]


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="minutes")


def normalize_domain(domain):
    domain = domain.strip().lower().removeprefix("https://").removeprefix("http://")
    return domain.removeprefix("www.").split("/")[0]


class Sheet:
    def __init__(self, service, sheet_id):
        self.values = service.spreadsheets().values()
        self.sheet_id = sheet_id

    def _read(self, tab, expected_columns):
        values = self.values.get(spreadsheetId=self.sheet_id, range=f"{tab}!A1:Z").execute().get("values", [])
        if not values:
            raise SystemExit(f"The {tab} tab is empty. Run setup_sheet.py first.")
        header = values[0]
        if header[: len(expected_columns)] != expected_columns:
            raise SystemExit(f"{tab} header must be exactly: {', '.join(expected_columns)}")
        rows = []
        for row_number, raw in enumerate(values[1:], start=2):
            row = {col: (raw[i].strip() if i < len(raw) else "") for i, col in enumerate(expected_columns)}
            row["_row"] = row_number
            rows.append(row)
        return rows

    def companies(self):
        rows = self._read(COMPANIES, COMPANY_COLUMNS)
        active = []
        for row in rows:
            if row["domain"] and row["active"].lower() not in ("no", "n", "false", "0"):
                row["domain"] = normalize_domain(row["domain"])
                active.append(row)
        return active

    def contacts(self):
        return self._read(CONTACTS, CONTACT_COLUMNS)

    def add_contacts(self, contacts):
        if not contacts:
            return
        self.values.append(
            spreadsheetId=self.sheet_id,
            range=f"{CONTACTS}!A1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [[c.get(col, "") for col in CONTACT_COLUMNS] for c in contacts]},
        ).execute()

    def update_contact(self, row):
        self.values.update(
            spreadsheetId=self.sheet_id,
            range=f"{CONTACTS}!A{row['_row']}",
            valueInputOption="RAW",
            body={"values": [[row.get(col, "") for col in CONTACT_COLUMNS]]},
        ).execute()
