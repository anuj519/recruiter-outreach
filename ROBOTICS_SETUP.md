# Robotics / Embedded Recruiter Outreach — Safe Setup

Tailored for a University of Michigan Robotics senior pursuing May 2027 new-grad full-time positions in robotics software, embedded systems, autonomy, controls and aerospace.

This branch changes the original project's defaults. **No real emails are sent until you explicitly configure Google OAuth and turn off DRY_RUN.** The Google connection has not been configured or live-tested.

## Safety changes
- `DRY_RUN=true` is the default; email and sheet changes are previewed, not executed.
- `DAILY_NEW_LIMIT` is capped at **5**, even if a larger environment value is provided.
- `AUTO_APPROVE` is forced **off in code**. Review each contact in the Google Sheet and manually change `status` to `approved`.
- Live sends require **both** `DRY_RUN=false` and `LIVE_SEND_CONFIRM=I_REVIEWED_CONTACTS`.
- Only one follow-up is sent after seven days, and the original reply detection remains intact.
- GitHub Actions schedules in the upstream repo remain disabled. Do not enable scheduled/live actions during testing.
- Old personalized internship templates from the original repository were removed to avoid accidental use.

## Template selection
The Contacts tab's `template` column can be:
- blank — general new-grad recruiter outreach (`templates/initial.txt`)
- `applied` — **only** for companies where you have actually submitted an application
- `startup` — for a small robotics/aerospace company or technical hiring manager

The `first_line` column in the Companies tab should contain a specific, accurate sentence about the company; do not invent projects or openings. Use Contacts `notes` for role title, application date, posting link and previous outreach. Default copy uses your UMich Robotics + CS minor, GM ADAS/HIL and C++/ROS 2 SLAM experience. **Read each email preview before approving.**

## Suggested first tests (no external recruiter emails)
1. Follow the upstream README to create a Python virtual environment, install `requirements.txt`, create a Google OAuth Desktop App and enable Gmail + Google Sheets APIs.
2. Copy `.env.example` to `.env`. Set `SENDER_NAME=Anuj Arora`, `DRY_RUN=true`, `AUTO_APPROVE=false`, `DAILY_NEW_LIMIT=5`, leave `LIVE_SEND_CONFIRM` empty. Never commit `.env` or OAuth credentials.
3. Run `python tests/test_robotics_setup.py` for offline template and safety checks.
4. Run `python auth_google.py` and `python setup_sheet.py` locally once configured. Add actual company domains to the Companies tab, and populate accurate `first_line` text.
5. Import contacts (Apollo CSV or verified manual CSV) and mark only your **own test email** as approved. You can manually add it with a target company's domain/company pair for the test; avoid falsely attributing it to a real recruiter.
6. Run `python send_emails.py` with `DRY_RUN=true`. Confirm the previewed subject, body, sender, recipient and first line. Nothing is sent.
7. For a delivery test to yourself only, temporarily set `DRY_RUN=false` and `LIVE_SEND_CONFIRM=I_REVIEWED_CONTACTS`, verify only your own email is approved, then run `python send_emails.py`. Restore `DRY_RUN=true` immediately. Inspect Gmail Sent and the Google Sheet.
8. Only after confirming results, review *each real recipient* and each personalized message before any live sends.

## Companies
`target_companies.csv` is a **planning list**, not an import-ready verified domain/contact list. It deliberately has empty domains. Verify official domains and recruiter identities before entering them into the sheet. Applied Intuition is on hold because an existing recruiter conversation is underway. Moby Robotics should be handled as a warm human connection rather than mass outreach.

## Public fork notice
This fork is public. It must contain **no API keys, refresh tokens, recruiter contact lists, private email addresses, or personal notes**. Prefer a private standalone copy before storing anything sensitive in a repository. GitHub Actions logs may expose recruiter email addresses.
