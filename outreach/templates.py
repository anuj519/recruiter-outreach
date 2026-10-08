"""Email templates in templates/. Fields: {first_name} {company} {first_line} {sender_name}.

initial.txt starts with a "Subject:" line. Follow-ups are replies, so they have no subject.
A company can override any template with templates/<domain>/<name>, e.g. templates/bloomberg.com/initial.txt.
A contact's "template" column picks a variant folder that wins over both, e.g. templates/alumni/.
"""

from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
NAMES = ["initial.txt", "followup_1.txt"]


def _path(name, domain="", variant=""):
    """Most specific first: a contact's template variant (e.g. alumni/), then the company, then the default."""
    for folder in (variant, domain):
        if folder and (TEMPLATE_DIR / folder / name).exists():
            return TEMPLATE_DIR / folder / name
    return TEMPLATE_DIR / name


def unfinished():
    return [str(p.relative_to(TEMPLATE_DIR)) for p in TEMPLATE_DIR.rglob("*.txt") if "TODO" in p.read_text()]


def render(name, domain="", variant="", **fields):
    text = _path(name, domain, variant).read_text()
    subject = None
    if text.startswith("Subject:"):
        first_line, _, text = text.partition("\n")
        subject = first_line.removeprefix("Subject:").strip().format_map(fields)
    return subject, text.strip().format_map(fields) + "\n"
