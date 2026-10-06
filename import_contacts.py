"""Import recruiters from a CSV into the Contacts tab. For the Apollo Free plan, which has no API access.

Export people from Apollo's website (or write a CSV by hand), then:
    python import_contacts.py export.csv            # preview
    python import_contacts.py export.csv --write     # add to the sheet

Only people at companies in the Companies tab are imported. Verified emails come in as "new",
everything else as "unverified", and AI-trap headlines as "skip". Duplicates are dropped.
"""

import argparse
import csv
from collections import Counter

from outreach import config
from outreach.filters import has_ai_trap
from outreach.google_client import credentials, sheets_service
from outreach.store import Sheet, normalize_domain, timestamp

# Apollo export headers first, then plain snake_case names for hand-made CSVs.
COLUMN_ALIASES = {
    "first_name": ["first name", "first_name"],
    "last_name": ["last name", "last_name"],
    "title": ["title"],
    "company": ["company", "company name", "company_name"],
    "email": ["email"],
    "email_status": ["email status", "email_status"],
    "linkedin_url": ["person linkedin url", "linkedin url", "linkedin_url"],
    "website": ["website", "domain"],
    "apollo_id": ["apollo contact id", "apollo_id"],
    "headline": ["headline"],
}


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = {h.strip().lower(): h for h in reader.fieldnames or []}
        columns = {field: next((headers[a] for a in aliases if a in headers), None) for field, aliases in COLUMN_ALIASES.items()}
        if not columns["email"]:
            raise SystemExit("CSV needs an Email column.")
        for raw in reader:
            yield {field: (raw.get(col) or "").strip() if col else "" for field, col in columns.items()}


def match_company(person, by_domain, by_name):
    """Find the person's company in the Companies tab by website, then company name, then email domain."""
    if person["website"]:
        company = by_domain.get(normalize_domain(person["website"]))
        if company:
            return company
    company = by_name.get(person["company"].lower())
    if company:
        return company
    return by_domain.get(person["email"].rpartition("@")[2].lower())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_path")
    parser.add_argument("--write", action="store_true", help="add rows to the sheet (default is preview only)")
    args = parser.parse_args()

    sheet = Sheet(sheets_service(credentials()), config.require("SHEET_ID"))
    companies = sheet.companies()
    by_domain = {c["domain"]: c for c in companies}
    by_name = {c["company"].lower(): c for c in companies if c["company"]}

    contacts = sheet.contacts()
    seen_emails = {c["email"].lower() for c in contacts if c["email"]}

    rows, skipped = [], Counter()
    for person in read_csv(args.csv_path):
        email = person["email"].lower()
        name = f"{person['first_name']} {person['last_name']}".strip() or email
        company = match_company(person, by_domain, by_name)
        if not email:
            skipped["no email"] += 1
            continue
        if not company:
            skipped["not a target company"] += 1
            print(f"  not a target company: {name} ({person['company'] or email})")
            continue
        if email in seen_emails:
            skipped["duplicate"] += 1
            continue
        seen_emails.add(email)

        if has_ai_trap(person["headline"]):
            status, notes = "skip", f"AI warning in headline: {person['headline']}"
        elif person["email_status"].lower() == "verified":
            status, notes = "new", ""
        else:
            status, notes = "unverified", ""

        rows.append({
            "company": company["company"] or company["domain"],
            "domain": company["domain"],
            "first_name": person["first_name"],
            "last_name": person["last_name"],
            "title": person["title"],
            "email": email,
            "email_status": person["email_status"].lower(),
            "linkedin_url": person["linkedin_url"],
            "apollo_id": person["apollo_id"],
            "status": status,
            "added_at": timestamp(),
            "follow_up_count": 0,
            "notes": notes,
        })
        print(f"  {status:<10} {name} | {person['title']} | {company['company']}")

    counts = Counter(r["status"] for r in rows)
    print(f"\n{counts['new']} new, {counts['unverified']} unverified, {counts['skip']} AI-warning skips; "
          f"dropped: {dict(skipped) or 'none'}")
    if args.write:
        sheet.add_contacts(rows)
        print(f"Added {len(rows)} rows to the sheet.")
    else:
        print("Preview only. Rerun with --write to add them.")


if __name__ == "__main__":
    main()
