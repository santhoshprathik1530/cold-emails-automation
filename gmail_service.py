"""
Gmail OAuth 2.0 authentication and email sending via Google API.

Setup:
1. Go to console.cloud.google.com → New project
2. Enable Gmail API
3. Credentials → Create → OAuth 2.0 Client ID → Desktop App
4. Download JSON → save as gmail_credentials.json in this folder
5. In the app, go to Settings → Connect Gmail
"""
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

_DIR        = Path(__file__).parent
TOKEN_FILE  = _DIR / ".gmail_token.json"
CREDS_FILE  = _DIR / "gmail_credentials.json"


# ─── Internal ─────────────────────────────────────────────────────────────────

def _load_creds():
    """Load credentials from token file, refreshing if expired."""
    # Check file existence BEFORE importing google packages (packages may not be installed yet)
    if not TOKEN_FILE.exists():
        return None
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request as GReq
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GReq())
            TOKEN_FILE.write_text(creds.to_json())
        return creds
    except Exception:
        return None


# ─── Public API ───────────────────────────────────────────────────────────────

def is_authenticated() -> bool:
    """Returns True if a valid Gmail token exists."""
    c = _load_creds()
    return c is not None and c.valid


def authenticate(creds_path=None) -> object:
    """
    Open browser OAuth flow. Saves token to .gmail_token.json.
    Blocks until user completes authorization.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    cf = str(creds_path or CREDS_FILE)
    if not Path(cf).exists():
        raise FileNotFoundError(
            f"Credentials file not found: {cf}\n"
            "Download gmail_credentials.json from Google Cloud Console → "
            "APIs & Services → Credentials → OAuth 2.0 Client ID (Desktop App)."
        )
    flow = InstalledAppFlow.from_client_secrets_file(cf, SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)
    TOKEN_FILE.write_text(creds.to_json())
    return creds


def get_sender_email() -> str | None:
    """Return the email address of the authenticated Gmail account."""
    try:
        from googleapiclient.discovery import build
        creds = _load_creds()
        if not creds or not creds.valid:
            return None
        svc = build("gmail", "v1", credentials=creds)
        return svc.users().getProfile(userId="me").execute().get("emailAddress")
    except Exception:
        return None


def send_email(
    to: str,
    subject: str,
    html_body: str,
    sender_name: str | None = None,
) -> dict:
    """
    Send an HTML email via Gmail API.
    Returns the API response dict (includes 'id' message ID).
    Raises RuntimeError if not authenticated.
    """
    from googleapiclient.discovery import build

    creds = _load_creds()
    if not creds or not creds.valid:
        raise RuntimeError(
            "Gmail not authenticated. Open the Settings tab → Connect Gmail."
        )

    svc = build("gmail", "v1", credentials=creds)
    msg = MIMEMultipart("alternative")
    msg["To"] = to
    msg["Subject"] = subject

    if sender_name:
        addr = get_sender_email()
        msg["From"] = f"{sender_name} <{addr}>" if addr else sender_name

    msg.attach(MIMEText(html_body, "html"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return svc.users().messages().send(userId="me", body={"raw": raw}).execute()
