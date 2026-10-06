"""Hunter.io client. The Free plan includes API access: 50 credits a month, 1 per domain search, 10 results max."""

import sys

import requests

from outreach import config

DOMAIN_SEARCH_URL = "https://api.hunter.io/v2/domain-search"
RECRUITER_WORDS = ("recruit", "talent", "sourcer", "sourcing", "university", "campus", "hiring")


class HunterError(Exception):
    pass


# The Free plan only returns the top 10 matches, so pull_contacts rotates through these weekly
# to surface different people.
SEARCH_TITLES = ["recruiter", "university recruiter", "talent acquisition", "technical recruiter", "campus recruiter"]


def search_recruiters(domain, job_title="recruiter"):
    """Return recruiters at `domain` matching `job_title`. Costs 1 credit if anything is found."""
    resp = requests.get(
        DOMAIN_SEARCH_URL,
        headers={"X-API-KEY": config.require("HUNTER_API_KEY")},
        # The verification_status filter hid valid results in testing, so verification is checked below instead.
        params={
            "domain": domain,
            "type": "personal",
            "job_titles": job_title,
            "limit": 10,  # Free plan maximum
        },
        timeout=30,
    )
    if resp.status_code == 401:
        raise HunterError("Hunter rejected HUNTER_API_KEY as invalid. Check the key in .env.")
    if resp.status_code == 429:
        raise HunterError("Hunter rate limit or monthly credit limit reached.")
    if not resp.ok:
        raise HunterError(f"Hunter returned {resp.status_code}: {resp.text[:300]}")

    people = []
    for e in resp.json().get("data", {}).get("emails", []):
        position = e.get("position") or ""
        if not any(word in position.lower() for word in RECRUITER_WORDS):
            continue  # department=hr also returns HR generalists, payroll, etc.
        people.append({
            "first_name": e.get("first_name") or "",
            "last_name": e.get("last_name") or "",
            "title": position,
            "email": (e.get("value") or "").lower(),
            "email_status": "verified" if (e.get("verification") or {}).get("status") == "valid" else "unverified",
            "linkedin_url": e.get("linkedin") or "",
        })
    return people


if __name__ == "__main__":
    # python -m outreach.hunter plaid.com  (costs 1 credit if results are found)
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m outreach.hunter <company-domain>")
    for p in search_recruiters(sys.argv[1]):
        print(f"{p['first_name']} {p['last_name']} | {p['title']} | {p['email_status']}")
