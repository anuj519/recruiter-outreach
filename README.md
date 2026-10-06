# Recruiter Outreach

Finds recruiters at target companies with Apollo, sends personalized cold emails from Gmail, and sends at most two follow-ups. Follow-ups stop as soon as anyone replies.

Everything runs in **dry-run mode by default**. Nothing is sent and no Apollo credits are spent until `DRY_RUN=false`.

## How it works

| Script | When | What it does |
|---|---|---|
| `pull_contacts.py` | weekly | Free Apollo search, then enriches up to `MAX_ENRICH_PER_RUN` people and adds verified emails to the sheet as `new` |
| `send_emails.py` | weekdays | Checks every contacted thread for replies, sends follow-ups that are due, then sends first emails to `approved` contacts |

The Google Sheet has two tabs.

- **Companies**: `domain`, `company`, `first_line` (the personalized opening line), `active` (set to `no` to pause a company)
- **Contacts**: one row per person. To approve someone, change `status` from `new` to `approved`. Set it to `skip` to never contact them.

Status flow: `new` → `approved` → `contacted` → `replied` / `opted_out` / `bounced` / `done`

## Setup

1. **Python env**
   ```zsh
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   # copy any lines missing from .env out of .env.example, then fill in SENDER_NAME
   ```
2. **Check Apollo access (free).** Run `python -m outreach.apollo stripe.com`. A 403 means the key needs People Search scope.
3. **Google OAuth client**
   - Go to [console.cloud.google.com](https://console.cloud.google.com), create a project, and enable the **Gmail API** and **Google Sheets API**.
   - On the OAuth consent screen, choose External and add yourself as a test user. Then click **Publish app**. If you leave it in Testing, refresh tokens expire after 7 days. You don't need to submit it for verification; Google just shows an "unverified app" warning when you consent.
   - Under Credentials, create an OAuth client ID of type **Desktop app**. Put its ID and secret in `.env`.
4. `python auth_google.py` opens a browser for consent and saves the refresh token to `.env`.
5. `python setup_sheet.py` creates the spreadsheet and saves `SHEET_ID` to `.env`.
6. Add companies to the Companies tab, then fill in every `TODO` in `templates/`. Live sends refuse to run while any `TODO` remains.
7. Try it locally:
   ```zsh
   python pull_contacts.py                  # dry run: shows who would be enriched
   DRY_RUN=false python pull_contacts.py    # spends credits, fills the sheet
   python send_emails.py                    # dry run: prints every email
   ```
   For the first real send, approve only a contact whose address is your own.

## GitHub Actions

Use a **private** repo. Run logs include recruiter names and emails.

- Secrets: `APOLLO_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `SHEET_ID`
- Variables: `SENDER_NAME`, plus optionally `DAILY_NEW_LIMIT` and `MAX_ENRICH_PER_RUN`

Both workflows are manual-only (Actions tab → Run workflow, with a dry-run checkbox). Once the results look right, uncomment the `schedule:` blocks. Scheduled runs are always live. GitHub disables scheduled workflows after 60 days without repo activity.

## Guardrails

- At most 20 new emails per run (`DAILY_NEW_LIMIT`), sent about 30 seconds apart
- At most 2 follow-ups, 7 days apart. Contacts are marked `done` 7 days after the last follow-up.
- Any human reply stops all emails to that person. Replies containing opt-out phrases are marked `opted_out`. Out-of-office auto-replies are ignored.
- Rows are never deleted, so a person or email already in the sheet is never re-added or re-enriched.
