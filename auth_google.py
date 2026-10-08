"""One-time local OAuth consent. Saves the refresh token into .env without printing it.

    python auth_google.py          # your Gmail (also owns the sheet)
    python auth_google.py umich    # your umich account, for sending only
"""

import sys

from dotenv import set_key
from google_auth_oauthlib.flow import InstalledAppFlow

from outreach import config
from outreach.google_client import ACCOUNTS, TOKEN_URI, gmail_service, scopes_for

account = sys.argv[1] if len(sys.argv) > 1 else "gmail"
if account not in ACCOUNTS:
    raise SystemExit(f"Unknown account '{account}'. Use one of: {', '.join(ACCOUNTS)}")

client_config = {
    "installed": {
        "client_id": config.require("GOOGLE_CLIENT_ID"),
        "client_secret": config.require("GOOGLE_CLIENT_SECRET"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": TOKEN_URI,
        "redirect_uris": ["http://localhost"],
    }
}

print(f"Sign in with your {account} account in the browser window.")
flow = InstalledAppFlow.from_client_config(client_config, scopes_for(account))
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
if not creds.refresh_token:
    raise SystemExit("Google did not return a refresh token. Remove the app's access at myaccount.google.com/permissions and retry.")

address = gmail_service(creds).users().getProfile(userId="me").execute()["emailAddress"]
set_key(".env", ACCOUNTS[account], creds.refresh_token)
print(f"Signed in as {address}. Saved {ACCOUNTS[account]} to .env")
