"""Daily job: check threads for replies, send due follow-ups, then send first emails to approved contacts.

With DRY_RUN on (the default) it prints every email and sheet change it would make, and sends or writes nothing.
"""

import random
import time
from datetime import datetime, timedelta, timezone
from email.utils import formataddr

from outreach import config, mailer, templates
from outreach.google_client import credentials, fresh_http, gmail_service, sheets_service
from outreach.lock import run_lock
from outreach.store import Sheet, timestamp


class Mailbox:
    """One sending account. Replies can only be checked in the mailbox that sent the email."""

    def __init__(self, account, creds=None):
        self.account = account
        self.creds = creds or credentials(account)
        self.gmail = gmail_service(self.creds)
        self.me = mailer.my_address(self.gmail)
        self.sender = formataddr((config.require("SENDER_NAME"), self.me))


class Outbox:
    def __init__(self, sheet, dry, mailboxes=None):
        self.sheet, self.dry = sheet, dry
        self.mailboxes = mailboxes or {}
        self.sent = 0

    def mailbox(self, row):
        """The contact's sending account (blank = gmail). Raises if that account isn't set up."""
        account = row.get("account") or "gmail"
        if account not in self.mailboxes:
            try:
                self.mailboxes[account] = Mailbox(account)
            except (SystemExit, Exception) as e:
                self.mailboxes[account] = e  # remembered so each row doesn't retry the login
        mb = self.mailboxes[account]
        if isinstance(mb, BaseException):
            raise RuntimeError(f"account '{account}' isn't connected ({mb}). Run: python auth_google.py {account}")
        return mb

    def send(self, row, subject, body, **threading):
        mb = self.mailbox(row)
        print(f"\n--> {row['first_name']} {row['last_name']} <{row['email']}> at {row['company']} (from {mb.me})")
        if self.dry:
            print(f"Subject: {subject}\n\n{body}")
            return None
        if self.sent:
            time.sleep(config.SEND_DELAY_SECONDS * random.uniform(0.75, 1.25))
        http = fresh_http(mb.creds) if mb.creds else None
        result = mailer.send(mb.gmail, sender=mb.sender, to=row["email"], subject=subject, body=body, http=http, **threading)
        self.sent += 1
        print("    sent")
        return result

    def save(self, row, **changes):
        row.update(changes)
        if self.dry:
            print(f"    [dry run] row {row['_row']} would update: {changes}")
        else:
            self.sheet.update_contact(row)


def fields(row, first_line=""):
    return {
        "first_name": row["first_name"],
        "company": row["company"],
        "first_line": first_line,
        "sender_name": config.require("SENDER_NAME"),
    }


def handle_follow_ups(outbox, contacts):
    now = datetime.now(timezone.utc)
    for row in contacts:
        if row["status"] != "contacted":
            continue
        if not row["thread_id"]:
            print(f"Row {row['_row']} is 'contacted' but has no thread_id. Skipping.")
            continue

        try:
            mb = outbox.mailbox(row)
            state = mailer.check_thread(mb.gmail, row["thread_id"], mb.me)
        except Exception as e:
            print(f"Couldn't check {row['email']}'s thread ({e}). Will retry next run.")
            continue
        if state.status != "waiting":
            print(f"{row['email']}: {state.status}, no more emails")
            outbox.save(row, status=state.status)
            continue

        last = datetime.fromisoformat(row["last_contacted"])
        if now - last < timedelta(days=config.FOLLOW_UP_DAYS):
            continue
        count = int(row["follow_up_count"] or 0)
        if count >= config.MAX_FOLLOW_UPS:
            outbox.save(row, status="done")
            continue

        _, body = templates.render(f"followup_{count + 1}.txt", row["domain"], row.get("template", ""), **fields(row))
        try:
            outbox.send(
                row, f"Re: {row['subject']}", body,
                thread_id=row["thread_id"], in_reply_to=state.last_message_id, references=state.references,
            )
        except Exception as e:
            # Counted as used rather than retried, so a send that actually went through is never duplicated.
            print(f"    follow-up failed ({e.__class__.__name__}); not retrying.")
            outbox.save(row, follow_up_count=count + 1, last_contacted=timestamp(), notes=f"Follow-up send failed: {e.__class__.__name__}")
            continue
        outbox.save(row, follow_up_count=count + 1, last_contacted=timestamp())


def handle_new(outbox, contacts, first_lines):
    approved = [r for r in contacts if r["status"] == "approved"]
    for row in approved[: config.DAILY_NEW_LIMIT]:
        if not row["first_name"]:
            print(f"Skipping {row['email']}: no first_name in the sheet.")
            continue
        try:
            outbox.mailbox(row)
        except RuntimeError as e:
            print(f"Skipping {row['email']}: {e}")
            continue
        subject, body = templates.render("initial.txt", row["domain"], row.get("template", ""), **fields(row, first_lines.get(row["domain"], "")))
        try:
            result = outbox.send(row, subject, body)
        except Exception as e:
            # Not retried: a timed-out send may have gone through. Check Sent before re-approving.
            print(f"    send failed ({e.__class__.__name__}); marked send_error. Check Gmail Sent before re-approving.")
            outbox.save(row, status="send_error", notes=f"Send failed {timestamp()}: {e.__class__.__name__}")
            continue
        if result:
            outbox.save(
                row, status="contacted", thread_id=result["threadId"], subject=subject,
                last_contacted=timestamp(), follow_up_count=0,
            )
    if len(approved) > config.DAILY_NEW_LIMIT:
        print(f"\n{len(approved) - config.DAILY_NEW_LIMIT} approved contacts left for later runs.")


def main():
    dry = config.DRY_RUN
    unfinished = templates.unfinished()
    if unfinished:
        if not dry:
            raise SystemExit(f"Templates still contain TODO: {', '.join(unfinished)}")
        print(f"Warning: templates still contain TODO: {', '.join(unfinished)}\n")

    gmail = Mailbox("gmail")  # also owns the sheet
    sheet = Sheet(sheets_service(gmail.creds), config.require("SHEET_ID"))
    outbox = Outbox(sheet, dry, {"gmail": gmail})

    contacts = sheet.contacts()
    first_lines = {c["domain"]: c["first_line"] for c in sheet.companies()}

    # Replies are checked before anything is sent.
    handle_follow_ups(outbox, contacts)
    handle_new(outbox, contacts, first_lines)

    print(f"\n{'Dry run, nothing sent.' if dry else f'Sent {outbox.sent} emails.'}")


if __name__ == "__main__":
    with run_lock():
        main()
