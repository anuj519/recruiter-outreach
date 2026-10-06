"""Weekly job: find recruiters at active companies, enrich a few, add verified ones as status "new".

With DRY_RUN on (the default) it runs only the free search and lists who would be enriched.
No credits are spent and the sheet is not changed.
"""

import re
from collections import Counter

from outreach import apollo, config
from outreach.google_client import credentials, sheets_service
from outreach.store import Sheet, timestamp

# Phrases recruiters put in their LinkedIn headline to catch AI-written outreach.
# Kept narrow on purpose: plain mentions of "LLM" or "AI" are common in tech recruiters' headlines.
AI_TRAP_PHRASES = (
    "if you are an ai", "if you're an ai", "if you are a bot", "if you're a bot",
    "if you are an llm", "if you're an llm", "if you are a language model", "if you're a language model",
    "if you are chatgpt", "if you're chatgpt", "ignore previous instructions", "ignore all previous",
    "ignore prior instructions", "ignore your instructions", "disregard previous instructions",
)


AI_TRAP_PATTERN = re.compile(r"\b(" + "|".join(re.escape(p) for p in AI_TRAP_PHRASES) + r")\b")


def has_ai_trap(text):
    return bool(AI_TRAP_PATTERN.search(text.lower().replace("’", "'")))


def main():
    dry = config.DRY_RUN
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

        people = apollo.search_people(domain, config.RECRUITER_TITLES, limit=want, exclude_ids=seen_ids)
        print(f"{domain}: {len(people)} to enrich")
        for p in people:
            print(f"  {p['first_name']} {p.get('last_name_obfuscated', '')} | {p.get('title')}")
        budget -= len(people)
        if dry or not people:
            continue

        rows = []
        for m in apollo.enrich([p["id"] for p in people]):
            email = (m.get("email") or "").lower()
            if email and email in seen_emails:
                print(f"  duplicate email, skipped: {m.get('name')}")
                continue
            verified = bool(email) and m.get("email_status") == "verified"
            headline = m.get("headline") or ""
            if has_ai_trap(headline):
                status, notes = "skip", f"AI warning in headline: {headline}"
            else:
                status, notes = ("new" if verified else "unverified"), ""
            rows.append({
                "company": company["company"] or domain,
                "domain": domain,
                "first_name": m.get("first_name") or "",
                "last_name": m.get("last_name") or "",
                "title": m.get("title") or "",
                "email": email,
                "email_status": m.get("email_status") or "",
                "linkedin_url": m.get("linkedin_url") or "",
                "apollo_id": m["id"],
                "status": status,
                "added_at": timestamp(),
                "follow_up_count": 0,
                "notes": notes,
            })
            seen_ids.add(m["id"])
            if email:
                seen_emails.add(email)
        sheet.add_contacts(rows)
        counts = Counter(r["status"] for r in rows)
        print(f"  added {counts['new']} verified, {counts['unverified']} unverified, {counts['skip']} skipped for AI warnings")

        if budget <= 0:
            print("Enrichment budget for this run used up.")
            break

    if dry:
        print("\nDry run: no credits spent, sheet unchanged. Set DRY_RUN=false to enrich.")


if __name__ == "__main__":
    main()
