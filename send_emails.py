"""Daily job: check threads for replies, send due follow-ups, then send first emails to approved contacts.

With DRY_RUN on (the default) it prints every email and sheet change it would make, and sends or writes nothing.
"""

import random
import time
from datetime import datetime, timedelta, timezone
from email.utils import formataddr

from outreach import config, mailer, templates
from outreach.google_client import credentials, gmail_service, sheets_service
from outreach.lock import run_lock
from outreach.store import Sheet, timestamp


class Outbox:
    def __init__(self, gmail, sheet, sender, dry):
        self.gmail, self.sheet, self.sender, self.dry = gmail, sheet, sender, dry
        self.sent = 0

    def send(self, row, subject, body, **threading):
        print(f"\n--> {row['first_name']} {row['last_name']} <{row['email']}> at {row['company']}")
        if self.dry:
            print(f"Subject: {subject}\n\n{body}")
            return None
        if self.sent:
            time.sleep(config.SEND_DELAY_SECONDS * random.uniform(0.75, 1.25))
        result = mailer.send(self.gmail, sender=self.sender, to=row["email"], subject=subject, body=body, **threading)
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


def handle_follow_ups(outbox, contacts, me):
    now = datetime.now(timezone.utc)
    for row in contacts:
        if row["status"] != "contacted":
            continue
        if not row["thread_id"]:
            print(f"Row {row['_row']} is 'contacted' but has no thread_id. Skipping.")
            continue

        state = mailer.check_thread(outbox.gmail, row["thread_id"], me)
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

        _, body = templates.render(f"followup_{count + 1}.txt", row["domain"], **fields(row))
        outbox.send(
            row, f"Re: {row['subject']}", body,
            thread_id=row["thread_id"], in_reply_to=state.last_message_id, references=state.references,
        )
        outbox.save(row, follow_up_count=count + 1, last_contacted=timestamp())


def handle_new(outbox, contacts, first_lines):
    approved = [r for r in contacts if r["status"] == "approved"]
    for row in approved[: config.DAILY_NEW_LIMIT]:
        subject, body = templates.render("initial.txt", row["domain"], **fields(row, first_lines.get(row["domain"], "")))
        result = outbox.send(row, subject, body)
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

    creds = credentials()
    gmail = gmail_service(creds)
    sheet = Sheet(sheets_service(creds), config.require("SHEET_ID"))
    me = mailer.my_address(gmail)
    outbox = Outbox(gmail, sheet, formataddr((config.require("SENDER_NAME"), me)), dry)

    contacts = sheet.contacts()
    first_lines = {c["domain"]: c["first_line"] for c in sheet.companies()}

    # Replies are checked before anything is sent.
    handle_follow_ups(outbox, contacts, me)
    handle_new(outbox, contacts, first_lines)

    print(f"\n{'Dry run, nothing sent.' if dry else f'Sent {outbox.sent} emails.'}")


if __name__ == "__main__":
    with run_lock():
        main()
