from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from outreach import config

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",  # reading threads for reply detection
    "https://www.googleapis.com/auth/spreadsheets",
]
TOKEN_URI = "https://oauth2.googleapis.com/token"


def credentials():
    creds = Credentials(
        token=None,
        refresh_token=config.require("GOOGLE_REFRESH_TOKEN"),
        client_id=config.require("GOOGLE_CLIENT_ID"),
        client_secret=config.require("GOOGLE_CLIENT_SECRET"),
        token_uri=TOKEN_URI,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def gmail_service(creds):
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def sheets_service(creds):
    return build("sheets", "v4", credentials=creds, cache_discovery=False)
