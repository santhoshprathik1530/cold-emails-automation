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
import json
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
_LAST_AUTH_ERROR = None


# ─── Internal ─────────────────────────────────────────────────────────────────

def _load_creds():
    """
    Load credentials from token file (local dev) or st.secrets (Streamlit Cloud).
    Refreshes the token if expired.
    """
    global _LAST_AUTH_ERROR
    _LAST_AUTH_ERROR = None
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request as GReq
    except ImportError:
        _LAST_AUTH_ERROR = "Google API packages are not installed."
        return None

    creds = None

    # 1. Try local token file first
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception as e:
            _LAST_AUTH_ERROR = f"Local Gmail token could not be loaded: {e}"
            creds = None

    # 2. Fall back to Streamlit secrets (Streamlit Cloud deployment)
    if creds is None:
        try:
            import streamlit as st
            token_val = (
                st.secrets.get("gmail_token_json")
                or st.secrets.get("GMAIL_TOKEN_JSON")
            )
            if token_val:
                info = json.loads(token_val) if isinstance(token_val, str) else dict(token_val)
                creds = Credentials.from_authorized_user_info(info, SCOPES)
            else:
                _LAST_AUTH_ERROR = (
                    "No Gmail token found. Add `gmail_token_json` to Streamlit secrets."
                )
        except Exception as e:
            _LAST_AUTH_ERROR = f"Streamlit Gmail token could not be loaded: {e}"

    if creds is None:
        return None

    # Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(GReq())
            # Persist refreshed token locally if possible (silently skip on cloud)
            try:
                TOKEN_FILE.write_text(creds.to_json())
            except Exception:
                pass
        except Exception as e:
            _LAST_AUTH_ERROR = f"Gmail token refresh failed: {e}"
            return None

    if not creds.valid:
        _LAST_AUTH_ERROR = "Gmail credentials are present but invalid."
        return None

    return creds


# ─── Public API ───────────────────────────────────────────────────────────────

def is_authenticated() -> bool:
    """Returns True if a valid Gmail token exists."""
    c = _load_creds()
    return c is not None and c.valid


def get_auth_error() -> str | None:
    """Return the most recent Gmail auth/load failure reason."""
    return _LAST_AUTH_ERROR


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


def clear_token() -> None:
    """Remove the local Gmail token so a fresh OAuth flow can start cleanly."""
    global _LAST_AUTH_ERROR
    _LAST_AUTH_ERROR = None
    try:
        TOKEN_FILE.unlink(missing_ok=True)
    except Exception:
        pass


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
