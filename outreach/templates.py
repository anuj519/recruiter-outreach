"""Email templates in templates/. Fields: {first_name} {company} {first_line} {sender_name}.

initial.txt starts with a "Subject:" line. Follow-ups are replies, so they have no subject.
"""

from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
NAMES = ["initial.txt", "followup_1.txt", "followup_2.txt"]


def unfinished():
    return [name for name in NAMES if "TODO" in (TEMPLATE_DIR / name).read_text()]


def render(name, **fields):
    text = (TEMPLATE_DIR / name).read_text()
    subject = None
    if text.startswith("Subject:"):
        first_line, _, text = text.partition("\n")
        subject = first_line.removeprefix("Subject:").strip().format_map(fields)
    return subject, text.strip().format_map(fields) + "\n"
