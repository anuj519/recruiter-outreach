"""Email templates in templates/. Fields: {first_name} {company} {first_line} {sender_name}.

initial.txt starts with a "Subject:" line. Follow-ups are replies, so they have no subject.
A company can override any template with templates/<domain>/<name>, e.g. templates/bloomberg.com/initial.txt.
"""

from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
NAMES = ["initial.txt", "followup_1.txt"]


def _path(name, domain=""):
    override = TEMPLATE_DIR / domain / name
    return override if domain and override.exists() else TEMPLATE_DIR / name


def unfinished():
    return [str(p.relative_to(TEMPLATE_DIR)) for p in TEMPLATE_DIR.rglob("*.txt") if "TODO" in p.read_text()]


def render(name, domain="", **fields):
    text = _path(name, domain).read_text()
    subject = None
    if text.startswith("Subject:"):
        first_line, _, text = text.partition("\n")
        subject = first_line.removeprefix("Subject:").strip().format_map(fields)
    return subject, text.strip().format_map(fields) + "\n"
