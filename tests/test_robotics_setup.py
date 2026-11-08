"""Offline checks. Run from repository root: python tests/test_robotics_setup.py"""
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
os.environ["DRY_RUN"] = "true"
os.environ["DAILY_NEW_LIMIT"] = "5"
os.environ["AUTO_APPROVE"] = "true"  # deliberate: confirm code ignores unsafe override

from outreach import config, templates

assert config.DRY_RUN is True
assert config.DAILY_NEW_LIMIT <= 5
assert config.AUTO_APPROVE is False
fields = dict(
    first_name="Taylor",
    company="Example Robotics",
    first_line="I'm interested in your work bringing robots into real-world settings.",
    sender_name="Anuj Arora",
)
for variant in ("", "applied", "startup"):
    subject, body = templates.render("initial.txt", "example.com", variant, **fields)
    assert subject and "Example Robotics" in subject
    assert "Taylor" in body and "Anuj Arora" in body
    assert "May 2027" in body
    assert "Nathan Done" not in body and "Summer 2027 internship" not in body
    assert "TODO" not in (subject + body)
    assert "{" not in (subject + body)
    print("PASS initial template:", variant or "default")

subject, body = templates.render("followup_1.txt", "example.com", "", **fields)
assert subject is None
assert "Taylor" in body and "Nathan Done" not in body
print("PASS follow-up template")
sender = (root / "send_emails.py").read_text()
assert "LIVE_SEND_CONFIRM" in sender and "I_REVIEWED_CONTACTS" in sender
print("PASS sender confirmation gate")
print("All offline robotics outreach smoke tests passed.")
