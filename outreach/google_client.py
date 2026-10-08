import httplib2
from google.auth.transport.requests import Request
from google_auth_httplib2 import AuthorizedHttp
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from outreach import config

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",  # reading threads for reply detection
]
SCOPES = GMAIL_SCOPES + ["https://www.googleapis.com/auth/spreadsheets"]
TOKEN_URI = "https://oauth2.googleapis.com/token"

# Sending accounts. "gmail" also owns the sheet; others only send and read their own threads.
ACCOUNTS = {"gmail": "GOOGLE_REFRESH_TOKEN", "umich": "GOOGLE_REFRESH_TOKEN_UMICH"}


def scopes_for(account):
    return SCOPES if account == "gmail" else GMAIL_SCOPES


def credentials(account="gmail"):
    if account not in ACCOUNTS:
        raise SystemExit(f"Unknown account '{account}'. Use one of: {', '.join(ACCOUNTS)}")
    creds = Credentials(
        token=None,
        refresh_token=config.require(ACCOUNTS[account]),
        client_id=config.require("GOOGLE_CLIENT_ID"),
        client_secret=config.require("GOOGLE_CLIENT_SECRET"),
        token_uri=TOKEN_URI,
        scopes=scopes_for(account),
    )
    creds.refresh(Request())
    return creds


def fresh_http(creds):
    """A new connection. Reusing one across the pause between sends gets it reset by Google."""
    return AuthorizedHttp(creds, http=httplib2.Http(timeout=60))


def gmail_service(creds):
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def sheets_service(creds):
    return build("sheets", "v4", credentials=creds, cache_discovery=False)
