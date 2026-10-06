"""Apollo.io client: free people search plus paid bulk enrichment."""

import sys
import time

import requests

from outreach import config

BASE_URL = "https://api.apollo.io/api/v1"


class ApolloError(Exception):
    pass


def _post(path, params=None, json=None):
    headers = {
        "x-api-key": config.require("APOLLO_API_KEY"),
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }
    for attempt in range(3):
        resp = requests.post(f"{BASE_URL}{path}", headers=headers, params=params, json=json, timeout=30)
        if resp.status_code == 429 and attempt < 2:
            time.sleep(30 * (attempt + 1))
            continue
        if resp.status_code == 403:
            raise ApolloError(f"{path} returned 403. The key may lack this endpoint's scope, or the plan may lack API access.")
        if not resp.ok:
            raise ApolloError(f"{path} returned {resp.status_code}: {resp.text[:300]}")
        return resp.json()


def search_people(domain, titles, limit, exclude_ids=(), per_page=25, max_pages=4):
    """Return up to `limit` people at `domain` with matching titles. Costs no credits.

    Last names come back obfuscated; enrichment reveals them.
    """
    found = []
    for page in range(1, max_pages + 1):
        params = [("person_titles[]", t) for t in titles] + [
            ("q_organization_domains_list[]", domain),
            ("include_similar_titles", "true"),
            ("page", page),
            ("per_page", per_page),
        ]
        people = _post("/mixed_people/api_search", params=params).get("people", [])
        for person in people:
            if person.get("has_email") and person["id"] not in exclude_ids:
                found.append(person)
                if len(found) >= limit:
                    return found
        if len(people) < per_page:
            break
    return found


def enrich(person_ids):
    """Bulk-enrich by Apollo id, 10 per call. Costs roughly 1 credit per person matched."""
    matches = []
    for i in range(0, len(person_ids), 10):
        chunk = person_ids[i : i + 10]
        data = _post(
            "/people/bulk_match",
            params={"reveal_personal_emails": "false"},
            json={"details": [{"id": pid} for pid in chunk]},
        )
        matches.extend(m for m in data.get("matches", []) if m)
    return matches


if __name__ == "__main__":
    # Free sanity check: python -m outreach.apollo stripe.com
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m outreach.apollo <company-domain>")
    for p in search_people(sys.argv[1], config.RECRUITER_TITLES, limit=25):
        print(f"{p['first_name']} {p.get('last_name_obfuscated', '')} | {p.get('title')} | {p['id']}")
