"""Weekly job: find recruiters at active companies and add verified ones to the sheet.

Uses Hunter.io when HUNTER_API_KEY is set (works on Hunter's Free plan), otherwise Apollo
(needs a paid Apollo plan). Verified emails are added as "new", or "approved" when
AUTO_APPROVE=true so the send job emails them without a manual review.

With DRY_RUN on (the default) it shows who would be added and leaves the sheet unchanged.
Hunter searches still cost a credit in dry run; Apollo dry runs only use the free search.
"""

import os
from collections import Counter

from outreach import apollo, config, hunter
from outreach.filters import has_ai_trap
from outreach.google_client import credentials, sheets_service
from outreach.store import Sheet, timestamp


def title_rank(title):
    """Front-line and university recruiters answer cold email more than recruiting leadership."""
    title = title.lower()
    if any(w in title for w in ("university", "campus", "early career", "emerging talent")):
        return 0
    if any(w in title for w in ("director", "head", "vp", "vice president", "chief", "manager", "operations")):
        return 2
    return 1


def find_with_hunter(domain, want, seen_emails):
    people = [p for p in hunter.search_recruiters(domain) if p["email"] not in seen_emails]
    people.sort(key=lambda p: (p["email_status"] != "verified", title_rank(p["title"])))
    return people[:want]


def find_with_apollo(domain, want, seen_ids, dry):
    found = apollo.search_people(domain, config.RECRUITER_TITLES, limit=want, exclude_ids=seen_ids)
    if dry:
        return [{"first_name": p["first_name"], "last_name": p.get("last_name_obfuscated", ""),
                 "title": p.get("title") or "", "email": "", "email_status": "(not enriched in dry run)"} for p in found]
    people = []
    for m in apollo.enrich([p["id"] for p in found]):
        headline = m.get("headline") or ""
        people.append({
            "first_name": m.get("first_name") or "",
            "last_name": m.get("last_name") or "",
            "title": m.get("title") or "",
            "email": (m.get("email") or "").lower(),
            "email_status": m.get("email_status") or "",
            "linkedin_url": m.get("linkedin_url") or "",
            "apollo_id": m["id"],
            "notes": f"AI warning in headline: {headline}" if has_ai_trap(headline) else "",
        })
    return people


def main():
    dry = config.DRY_RUN
    use_hunter = bool(os.getenv("HUNTER_API_KEY"))
    print(f"Source: {'Hunter' if use_hunter else 'Apollo'}{' (dry run)' if dry else ''}\n")

    sheet = Sheet(sheets_service(credentials()), config.require("SHEET_ID"))
    contacts = sheet.contacts()
    seen_ids = {c["apollo_id"] for c in contacts if c["apollo_id"]}
    seen_emails = {c["email"].lower() for c in contacts if c["email"]}
    per_company = Counter(c["domain"] for c in contacts if c["status"] != "unverified")
    budget = config.MAX_ENRICH_PER_RUN

    for company in sheet.companies():
        domain = company["domain"]
        want = min(config.MAX_PER_COMPANY - per_company[domain], budget)
        if want <= 0:
            continue

        if use_hunter:
            people = find_with_hunter(domain, want, seen_emails)
        else:
            people = find_with_apollo(domain, want, seen_ids, dry)
        budget -= len(people)

        rows = []
        for p in people:
            email = p["email"]
            if email and email in seen_emails:
                continue
            if p.get("notes"):
                status = "skip"
            elif email and p["email_status"] == "verified":
                status = "approved" if config.AUTO_APPROVE else "new"
            else:
                status = "unverified"
            rows.append({
                **p,
                "company": company["company"] or domain,
                "domain": domain,
                "status": status,
                "added_at": timestamp(),
                "follow_up_count": 0,
            })
            if email:
                seen_emails.add(email)
            if p.get("apollo_id"):
                seen_ids.add(p["apollo_id"])

        print(f"{domain}: {len(rows)} found")
        for r in rows:
            print(f"  {r['status']:<10} {r['first_name']} {r['last_name']} | {r['title']}")
        if rows and not dry:
            sheet.add_contacts(rows)

        if budget <= 0:
            print("Per-run contact budget used up.")
            break

    if dry:
        print("\nDry run: sheet unchanged. Set DRY_RUN=false to add these contacts.")


if __name__ == "__main__":
    main()
