"""Gmail sending and reply detection."""

import base64
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import parseaddr

BOUNCE_SENDERS = ("mailer-daemon", "postmaster")
OPT_OUT_PHRASES = (
    "unsubscribe", "remove me", "take me off", "do not contact", "don't contact",
    "dont contact", "stop emailing", "stop contacting", "not interested",
)
# Higher wins when a thread has several kinds of messages.
PRIORITY = {"waiting": 0, "bounced": 1, "replied": 2, "opted_out": 3}


@dataclass
class ThreadState:
    status: str  # waiting | replied | opted_out | bounced
    last_message_id: str
    references: str


def my_address(gmail):
    return gmail.users().getProfile(userId="me").execute(num_retries=3)["emailAddress"]


def send(gmail, *, sender, to, subject, body, thread_id=None, in_reply_to=None, references=None):
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = f"{references or ''} {in_reply_to}".strip()
    msg.set_content(body)

    payload = {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()}
    if thread_id:
        payload["threadId"] = thread_id
    return gmail.users().messages().send(userId="me", body=payload).execute()


def check_thread(gmail, thread_id, me):
    thread = gmail.users().threads().get(
        userId="me",
        id=thread_id,
        format="metadata",
        metadataHeaders=["From", "Message-ID", "References", "Auto-Submitted"],
    ).execute(num_retries=3)

    status, last_id, refs = "waiting", "", ""
    for message in thread.get("messages", []):
        headers = {h["name"].lower(): h["value"] for h in message["payload"].get("headers", [])}
        last_id = headers.get("message-id", last_id)
        refs = headers.get("references", refs)

        sender = parseaddr(headers.get("from", ""))[1].lower()
        if sender == me.lower():
            continue
        if sender.split("@")[0] in BOUNCE_SENDERS:
            found = "bounced"
        elif headers.get("auto-submitted", "no").lower() != "no":
            continue  # out-of-office and similar auto-replies don't stop follow-ups
        elif any(p in message.get("snippet", "").lower() for p in OPT_OUT_PHRASES):
            found = "opted_out"
        else:
            found = "replied"
        if PRIORITY[found] > PRIORITY[status]:
            status = found

    return ThreadState(status, last_id, refs)
