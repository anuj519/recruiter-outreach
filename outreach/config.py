import os

from dotenv import load_dotenv

load_dotenv()


def _int(name, default):
    return int(os.getenv(name) or default)


def require(name):
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing setting {name}. Set it in .env locally or as a GitHub secret.")
    return value


# Dry run is on unless explicitly turned off, so nothing sends by accident.
DRY_RUN = os.getenv("DRY_RUN", "true").strip().lower() != "false"

DAILY_NEW_LIMIT = _int("DAILY_NEW_LIMIT", 20)
MAX_FOLLOW_UPS = min(_int("MAX_FOLLOW_UPS", 1), 1)  # one follow-up, then stop
FOLLOW_UP_DAYS = float(os.getenv("FOLLOW_UP_DAYS") or 7)  # fractions allowed, e.g. 1.5
SEND_DELAY_SECONDS = _int("SEND_DELAY_SECONDS", 30)

# When true, verified contacts are added as "approved" and get emailed without a manual review.
AUTO_APPROVE = os.getenv("AUTO_APPROVE", "false").strip().lower() == "true"

MAX_ENRICH_PER_RUN = _int("MAX_ENRICH_PER_RUN", 20)  # contacts added per pull, at most
MAX_PER_COMPANY = _int("MAX_PER_COMPANY", 3)

RECRUITER_TITLES = [
    "recruiter",
    "technical recruiter",
    "university recruiter",
    "campus recruiter",
    "talent acquisition",
]
