"""One-time local OAuth consent. Saves the refresh token into .env without printing it."""

from dotenv import set_key
from google_auth_oauthlib.flow import InstalledAppFlow

from outreach import config
from outreach.google_client import SCOPES, TOKEN_URI

client_config = {
    "installed": {
        "client_id": config.require("GOOGLE_CLIENT_ID"),
        "client_secret": config.require("GOOGLE_CLIENT_SECRET"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": TOKEN_URI,
        "redirect_uris": ["http://localhost"],
    }
}

flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
if not creds.refresh_token:
    raise SystemExit("Google did not return a refresh token. Remove the app's access at myaccount.google.com/permissions and retry.")

set_key(".env", "GOOGLE_REFRESH_TOKEN", creds.refresh_token)
print("Saved GOOGLE_REFRESH_TOKEN to .env")
