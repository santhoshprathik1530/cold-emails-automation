"""
🚀 Cold Email Hub
Unified app: Find contacts via Apollo · Send emails via Gmail · Track opens.

Run:  streamlit run app.py
"""

import json
import math
import os
import time
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

CDT = ZoneInfo("America/Chicago")
from urllib.parse import quote_plus

import pandas as pd
import requests as req
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG + CSS
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Cold Email Hub",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
*, body, .stApp { font-family: 'Inter', sans-serif !important; }
.stApp { background-color: #08090d; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; }

div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea,
div[data-baseweb="select"] {
    background: #0f1117 !important; border-color: #1e2130 !important;
    color: #e2e4ed !important; border-radius: 8px !important; font-size: 0.875rem !important;
}
div[data-baseweb="tag"] { background: #5a5fcf !important; border-radius: 4px !important; }
input::placeholder, textarea::placeholder { color: #3a3f55 !important; }

label, .stTextInput label, .stMultiSelect label,
.stTextArea label, .stNumberInput label {
    color: #3a3f55 !important; font-size: 0.7rem !important; font-weight: 600 !important;
    letter-spacing: 0.08em !important; text-transform: uppercase !important;
}

.stButton > button {
    background: transparent; border: 1px solid #1e2130; color: #5a5f7a;
    border-radius: 7px; font-size: 0.8rem; font-weight: 500;
    padding: 0.45rem 1rem; transition: all 0.15s;
}
.stButton > button:hover { border-color: #5a5fcf; color: #8486e0; background: #0f1117; }
.stButton > button[kind="primary"] {
    background: #5a5fcf; border-color: #5a5fcf; color: #fff; font-weight: 600;
}
.stButton > button[kind="primary"]:hover { background: #4a4fbf; border-color: #4a4fbf; }
.stButton > button:disabled { opacity: 0.35 !important; cursor: not-allowed !important; }

.stDownloadButton > button {
    background: transparent !important; border: 1px solid #1e2130 !important;
    color: #5a5f7a !important; border-radius: 7px !important; font-size: 0.78rem !important;
}

.stDataFrame, [data-testid="stDataFrameResizable"] {
    border: 1px solid #1e2130 !important; border-radius: 10px !important; overflow: hidden;
}
.divider { border: none; border-top: 1px solid #13151f; margin: 1.5rem 0; }

.metric-wrap {
    background: #0f1117; border: 1px solid #1c1f2e;
    border-radius: 12px; padding: 1.2rem 1.4rem;
}
.metric-label {
    font-size: 0.72rem; font-weight: 500; letter-spacing: 0.08em;
    text-transform: uppercase; color: #4b5270; margin-bottom: 0.5rem;
}
.metric-value { font-size: 2rem; font-weight: 300; color: #e8eaf0; line-height: 1; }
.metric-sub   { font-size: 0.75rem; color: #3ecf8e; font-weight: 500; }
.metric-sub.warn  { color: #f87171; }
.metric-sub.muted { color: #4b5270; }

.stat { background: #0f1117; border: 1px solid #1e2130; border-radius: 10px;
        padding: 0.9rem 1.2rem; text-align: center; }
.stat-n { font-size: 1.75rem; font-weight: 300; color: #e2e4ed; line-height: 1; }
.stat-l { font-size: 0.65rem; letter-spacing: 0.1em; text-transform: uppercase;
          color: #3a3f55; font-weight: 600; margin-top: 0.35rem; }

.sec { font-size: 0.68rem; letter-spacing: 0.1em; text-transform: uppercase;
       color: #3a3f55; font-weight: 600; margin-bottom: 0.6rem; }

div[data-testid="stExpander"] {
    background: #0f1117; border: 1px solid #1c1f2e !important;
    border-radius: 10px; margin-bottom: 0.5rem;
}

.pill-status {
    display: inline-block; padding: 0.18rem 0.7rem; border-radius: 999px;
    font-size: 0.68rem; font-weight: 600; letter-spacing: 0.06em;
}
.pill-ok  { background: #0e2a1c; color: #3ecf8e; }
.pill-err { background: #2a0e0e; color: #f87171; }

button[data-baseweb="tab"] { color: #3a3f55 !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: #e2e4ed !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG HELPERS
# ─────────────────────────────────────────────────────────────────────────────

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), ".app_settings.json")


def _load_settings() -> dict:
    try:
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_settings(d: dict):
    existing = _load_settings()
    existing.update(d)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(existing, f, indent=2)


def _cfg(key: str, fallback: str = "") -> str:
    """Priority: env var -> settings file -> Streamlit secrets -> fallback."""
    env_val = os.getenv(key.upper())
    if env_val:
        return env_val
    s = _load_settings()
    if key.lower() in s:
        return s[key.lower()]
    try:
        return st.secrets.get(key.lower(), fallback)
    except Exception:
        return fallback


APOLLO_KEY   = _cfg("APOLLO_API_KEY", "l8TMBu3V3n6o8aDuENZcNA")
SB_URL       = _cfg("SUPABASE_URL")
SB_KEY       = _cfg("SUPABASE_KEY")
_SB_FN_BASE  = f"{SB_URL}/functions/v1" if SB_URL else ""
TRACKING_URL = _cfg("TRACKING_URL", _SB_FN_BASE)
SENDER_NAME  = _cfg("SENDER_NAME", "")
RESUME_URL   = _cfg("RESUME_URL", "")
LINKEDIN_URL = _cfg("LINKEDIN_URL", "")
WEBSITE_URL  = _cfg("WEBSITE_URL", "")
APP_USERNAME = _cfg("APP_USERNAME", "")
APP_PASSWORD = _cfg("APP_PASSWORD", "")

APOLLO_H = {
    "Content-Type": "application/json",
    "Cache-Control": "no-cache",
    "accept": "application/json",
    "x-api-key": APOLLO_KEY,
}


# ─────────────────────────────────────────────────────────────────────────────
# SUPABASE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _sbh(prefer: str = "return=minimal") -> dict:
    h = {
        "apikey": SB_KEY,
        "Authorization": f"Bearer {SB_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def sb_get(table: str, params: str = "") -> list:
    if not SB_URL or not SB_KEY:
        return []
    try:
        r = req.get(
            f"{SB_URL}/rest/v1/{table}?{params}",
            headers=_sbh(""),
            timeout=10,
        )
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def sb_insert(table: str, rows: list | dict, upsert: bool = False) -> bool:
    if not SB_URL or not SB_KEY:
        return False
    prefer = "resolution=merge-duplicates,return=minimal" if upsert else "return=minimal"
    try:
        r = req.post(
            f"{SB_URL}/rest/v1/{table}",
            headers=_sbh(prefer),
            json=rows,
            timeout=10,
        )
        return r.status_code in (200, 201)
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# GMAIL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def gmail_ok() -> bool:
    try:
        from gmail_service import is_authenticated
        return is_authenticated()
    except Exception:
        return False


def gmail_sender_addr() -> str | None:
    try:
        from gmail_service import get_sender_email
        return get_sender_email()
    except Exception:
        return None


def gmail_send(to: str, subject: str, html: str) -> dict:
    from gmail_service import send_email
    sn = _cfg("SENDER_NAME", "")
    return send_email(to, subject, html, sender_name=sn or None)


def gmail_connect():
    from gmail_service import authenticate
    return authenticate()


# DEFAULTS — subject + HTML template (kept simple and ASCII-safe)
DEFAULT_SUBJECT = "Summer 2026 Internship - Data Analytics / DS / AI | Santhosh Prathik Kasam"

DEFAULT_TEMPLATE = """
<div style="font-family: Arial, sans-serif; font-size: 14px; color: #222; max-width: 600px; line-height: 1.7;">

    <p>Hello {first_name},</p>

    <p>
        I'm <strong>Santhosh Prathik Kasam</strong>, a Masters Data Science student at the
        University of Illinois Chicago (GPA 4.0, graduating Dec 2026), reaching out to ask if
        <strong>{company}</strong> has any <strong>Summer 2026 internship opportunities</strong> in
        Data Analytics, Data Science, or AI.
    </p>

    <p>
        I am currently based in <strong>Chicago</strong> and available full-time from
        <strong>May-August 2026</strong>, open to relocating anywhere in the United States for the
        right opportunity. I also have work authorization for internship roles in the U.S.
    </p>

    <p>
        If there are openings or if you could direct me to the right team, I would greatly
        appreciate it.
    </p>

    <p>I have included my profile details below:</p>

    <p>
        📄 <a href="{resume_link}" style="color:#1a56db;">Resume</a> &nbsp;&nbsp;
        💼 <a href="{linkedin_link}" style="color:#1a56db;">LinkedIn</a> &nbsp;&nbsp;
        🌐 <a href="{website_link}" style="color:#1a56db;">Website</a>
    </p>

    <p>Best,</p>
    <p>
        <strong>Santhosh Prathik Kasam</strong><br>
        Personal: kasamsanthoshprathik@gmail.com<br>
        College: skasa@uic.edu<br>
        Mobile: (331) 230-5217
    </p>

</div>"""


def _wrap_link(url: str, email_id: str, link_type: str, tracking_url: str) -> str:
    """Wrap a URL through the tracking redirect endpoint."""
    if not url or not tracking_url:
        return url or "#"
    encoded = quote_plus(url)
    return f"{tracking_url}/track/link/{email_id}?url={encoded}&type={link_type}"


def _pixel(email_id: str, tracking_url: str) -> str:
    return (
        f'<img src="{tracking_url}/track/open/{email_id}.gif" '
        'width="1" height="1" style="display:none;" alt="">'
    )


def build_email_html(
    template: str,
    first_name: str,
    company: str,
    email_id: str,
    sender_name: str,
    resume_url: str,
    linkedin_url: str,
    website_url: str,
    tracking_url: str,
) -> str:
    """Substitute template variables and inject tracking pixel + link wrappers."""
    html = template.replace("{first_name}", first_name or "there")
    html = html.replace("{company}", company or "your company")
    html = html.replace("{sender_name}", sender_name or "")
    html = html.replace("{resume_link}",   _wrap_link(resume_url,   email_id, "resume",   tracking_url))
    html = html.replace("{linkedin_link}", _wrap_link(linkedin_url, email_id, "linkedin", tracking_url))
    html = html.replace("{website_link}",  _wrap_link(website_url,  email_id, "website",  tracking_url))
    # Append tracking pixel
    html += _pixel(email_id, tracking_url)
    return html


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE DEFAULTS
# ─────────────────────────────────────────────────────────────────────────────

_defaults = {
    "search_results":  [],
    "enriched_results": [],
    "select_all":      False,
    "send_contacts":   [],   # contacts queued for the Send tab
    "active_filter":   "All",
    "followup_days":   3,
    "email_template":  DEFAULT_TEMPLATE,
    "authenticated":   False,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────────────────
# AUTH HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _is_authenticated() -> bool:
    return st.session_state.get("authenticated", False)


@st.dialog("🔒 Sign in required")
def _show_login_dialog():
    st.caption("This action requires authentication.")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Sign in", type="primary", use_container_width=True):
        if username == APP_USERNAME and password == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect username or password.")


# ─────────────────────────────────────────────────────────────────────────────
# FIRST-RUN SETUP — runs before tabs if Gmail not connected
# ─────────────────────────────────────────────────────────────────────────────

_CREDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gmail_credentials.json")
_TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".gmail_token.json")


def _google_pkgs_ok() -> bool:
    try:
        import google.oauth2.credentials          # noqa
        import google_auth_oauthlib.flow          # noqa
        import googleapiclient.discovery          # noqa
        return True
    except ImportError:
        return False


if not _google_pkgs_ok():
    st.markdown(
        '<h2 style="color:#e2e4ed;font-weight:600;">🚀 Cold Email Hub — Setup</h2>',
        unsafe_allow_html=True,
    )
    st.error("Google API packages are not installed. Run the command below, then restart the app.")
    st.code("pip install google-auth google-auth-oauthlib google-api-python-client", language="bash")
    st.stop()

elif not os.path.exists(_TOKEN_FILE) and not st.secrets.get("gmail_token_json"):
    # Gmail not yet authorised — show a dedicated connect screen
    st.markdown(
        '<h2 style="color:#e2e4ed;font-weight:600;margin-bottom:0;">🚀 Cold Email Hub</h2>'
        '<p style="color:#3a3f55;font-size:0.8rem;margin-top:0.1rem;margin-bottom:2rem;">'
        'One-time setup — connect your Gmail account to get started</p>',
        unsafe_allow_html=True,
    )

    col_card, _ = st.columns([2, 3])
    with col_card:
        st.markdown(
            '<div style="background:#0f1117;border:1px solid #1e2130;border-radius:14px;padding:2rem;">'
            '<p style="color:#e2e4ed;font-size:1rem;font-weight:600;margin-bottom:0.4rem;">Connect Gmail</p>'
            '<p style="color:#4b5270;font-size:0.82rem;margin-bottom:1.5rem;">'
            'The app will open a browser tab — sign in and allow access. '
            'Your token is saved locally and never leaves this machine.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button("🔗 Connect Gmail", type="primary", use_container_width=True):
            with st.spinner("Opening browser for Gmail authorization…"):
                try:
                    gmail_connect()
                    st.success("✅ Gmail connected!")
                    time.sleep(1)
                    st.rerun()
                except FileNotFoundError:
                    st.error(
                        "gmail_credentials.json not found. "
                        "For local use: download it from Google Cloud Console and place it in the app folder. "
                        "For Streamlit Cloud: add your Gmail token to app secrets as `gmail_token_json` "
                        "(copy the contents of .gmail_token.json after authenticating locally)."
                    )
                except Exception as e:
                    st.error(f"Auth failed: {e}")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

is_gmail = gmail_ok()
gmail_pill = (
    '<span class="pill-status pill-ok">● Gmail connected</span>'
    if is_gmail
    else '<span class="pill-status pill-err">● Gmail not connected</span>'
)

h1, h2, h3 = st.columns([6, 2, 1])
with h1:
    st.markdown(
        '<h2 style="color:#e2e4ed;font-weight:600;margin-bottom:0;">🚀 Cold Email Hub</h2>'
        '<p style="color:#3a3f55;font-size:0.8rem;margin-top:0.1rem;">'
        'Find contacts &nbsp;·&nbsp; Send emails &nbsp;·&nbsp; Track opens'
        '</p>',
        unsafe_allow_html=True,
    )
with h2:
    st.markdown(
        f'<p style="text-align:right;padding-top:1.2rem;">{gmail_pill}</p>',
        unsafe_allow_html=True,
    )
with h3:
    st.markdown("<br>", unsafe_allow_html=True)
    if _is_authenticated():
        if st.button("🔓 Sign out", use_container_width=True, key="signout_btn"):
            st.session_state.authenticated = False
            st.rerun()
    else:
        if st.button("🔒 Sign in", use_container_width=True, key="signin_header_btn"):
            _show_login_dialog()

st.markdown('<hr class="divider">', unsafe_allow_html=True)

tab_find, tab_send, tab_dash, tab_settings = st.tabs([
    "🔍  Find",
    "📧  Send",
    "📊  Dashboard",
    "⚙️  Settings",
])


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — FIND CONTACTS
# ═════════════════════════════════════════════════════════════════════════════

with tab_find:

    HR_TITLES_ALL = [
        "hr", "talent acquisition", "hiring", "recruiter", "recruiting",
        "recruitment", "resource", "sourcer", "sourcing",
        "people ops", "people operations", "workforce",
        "staffing", "human resources", "hrbp", "talent partner",
    ]
    HR_TITLES_DEF = HR_TITLES_ALL[:9]

    LOCS_ALL = [
        "chicago", "new york", "los angeles", "houston", "phoenix",
        "philadelphia", "san antonio", "san diego", "dallas", "san jose",
        "austin", "jacksonville", "san francisco", "columbus", "seattle",
        "denver", "boston", "nashville", "atlanta", "miami",
        "united states", "canada", "united kingdom",
    ]

    # ── API functions ────────────────────────────────────────────────────────

    def _search_companies(query: str) -> list:
        r = req.post(
            "https://api.apollo.io/api/v1/mixed_companies/search",
            headers=APOLLO_H,
            json={"q_organization_name": query, "page": 1, "per_page": 10},
            timeout=15,
        )
        return r.json().get("organizations", []) if r.status_code == 200 else []

    def _search_people(org_ids, locations, titles, target) -> list:
        all_p, per = [], 100
        max_pg = min(500, math.ceil(target / per) + 2)
        for oid in org_ids:
            for loc in locations:
                page = 1
                while page <= max_pg:
                    r = req.post(
                        "https://api.apollo.io/api/v1/mixed_people/api_search",
                        headers=APOLLO_H,
                        json={
                            "organization_ids": [oid],
                            "contact_email_status": ["verified"],
                            "person_titles": titles,
                            "person_locations": [loc],
                            "page": page, "per_page": per,
                        },
                        timeout=20,
                    )
                    if r.status_code != 200:
                        break
                    people = r.json().get("people", [])
                    if not people:
                        break
                    all_p.extend(people)
                    if len(all_p) >= target or len(people) < per:
                        break
                    page += 1
                if len(all_p) >= target:
                    break
            if len(all_p) >= target:
                break
        return all_p[:target]

    def _enrich_people(people: list) -> list:
        matches = []
        for i in range(0, len(people), 10):
            chunk = people[i:i + 10]
            r = req.post(
                "https://api.apollo.io/api/v1/people/bulk_match",
                headers=APOLLO_H,
                json={"details": [{"id": p["id"]} for p in chunk]},
                timeout=20,
            )
            if r.status_code == 200:
                matches.extend(r.json().get("matches", []))
        return matches

    def _save_contacts(people: list) -> int:
        rows = []
        for p in people:
            org = p.get("organization") or {}
            rows.append({
                "apollo_id":       p.get("id"),
                "first_name":      p.get("first_name"),
                "last_name":       p.get("last_name"),
                "name":            p.get("name"),
                "title":           p.get("title"),
                "headline":        p.get("headline"),
                "email":           p.get("email"),
                "email_status":    p.get("email_status"),
                "linkedin_url":    p.get("linkedin_url"),
                "photo_url":       p.get("photo_url"),
                "organization_id": p.get("organization_id"),
                "company":         org.get("name") if isinstance(org, dict) else None,
                "city":            p.get("city"),
                "state":           p.get("state"),
                "country":         p.get("country"),
            })
        if rows and sb_insert("hr_contacts", rows, upsert=True):
            return len(rows)
        return 0

    # ── Company lookup UI ────────────────────────────────────────────────────

    st.markdown('<p class="sec">Company Lookup — find Apollo Org ID by name</p>', unsafe_allow_html=True)
    cq1, cq2 = st.columns([4, 1])
    with cq1:
        company_q = st.text_input("Company name", placeholder="e.g. Google, Stripe, Duolingo", key="company_q")
    with cq2:
        st.markdown("<br>", unsafe_allow_html=True)
        co_btn = st.button("Look up", key="co_btn")

    if co_btn and company_q:
        with st.spinner(f"Searching Apollo for '{company_q}'..."):
            orgs = _search_companies(company_q)
        if orgs:
            org_df = pd.DataFrame([{
                "Org ID":    o.get("id", "—"),
                "Name":      o.get("name", "—"),
                "Domain":    o.get("primary_domain", "—"),
                "Employees": o.get("estimated_num_employees", "—"),
                "City":      o.get("city", "—"),
            } for o in orgs])
            st.dataframe(org_df, use_container_width=True, hide_index=True)
            st.caption("📋 Copy an Org ID from the table above and paste it into the field below.")
        else:
            st.warning("No companies found — try a shorter name.")

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── People search UI ─────────────────────────────────────────────────────

    st.markdown('<p class="sec">Search HR Contacts</p>', unsafe_allow_html=True)

    fc1, fc2 = st.columns([4, 1])
    with fc1:
        org_ids_raw = st.text_input(
            "Org ID(s)", placeholder="Comma-separated Apollo org IDs", key="find_orgids"
        )
    with fc2:
        target_count = st.number_input("Max results", 1, 1000, 40, key="find_tgt")

    lc1, lc2 = st.columns([1, 2])
    with lc1:
        locations = st.multiselect("Locations", LOCS_ALL, default=["chicago"], key="find_locs")
    with lc2:
        titles = st.multiselect("Title keywords", HR_TITLES_ALL, default=HR_TITLES_DEF, key="find_titles")

    st.markdown("<br style='line-height:0.2'>", unsafe_allow_html=True)

    has_results  = bool(st.session_state.search_results)
    has_enriched = bool(st.session_state.enriched_results)

    b1, b2, b3, b4, _ = st.columns([1, 1, 1, 1, 3])
    with b1: search_btn  = st.button("Search",     type="primary", use_container_width=True)
    with b2: enrich_btn  = st.button("Enrich",     type="primary", use_container_width=True, disabled=not has_results)
    with b3: sel_all_btn = st.button("Select All", use_container_width=True, disabled=not has_results)
    with b4: clear_btn   = st.button("Clear",      use_container_width=True, disabled=not has_results)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Handle button actions ────────────────────────────────────────────────

    if search_btn:
        org_ids = [o.strip() for o in org_ids_raw.split(",") if o.strip()]
        if not org_ids:
            st.error("Enter at least one Org ID.")
        elif not locations:
            st.error("Select at least one location.")
        elif not titles:
            st.error("Select at least one title keyword.")
        else:
            with st.spinner(f"Searching for up to {target_count} HR contacts..."):
                results = _search_people(org_ids, locations, titles, target_count)
            st.session_state.search_results  = results
            st.session_state.enriched_results = []
            st.session_state.select_all = False
            st.session_state.pop("find_tbl", None)   # reset checkbox state for new results
            if results:
                st.success(f"✅ Found {len(results)} contacts")

    if sel_all_btn:
        st.session_state.select_all = True
        st.session_state.pop("find_tbl", None)   # clear delta edits so all rows render as checked
    if clear_btn:
        st.session_state.select_all = False
        st.session_state.pop("find_tbl", None)   # clear delta edits so all rows render as unchecked

    if enrich_btn and st.session_state.search_results:
        if not _is_authenticated():
            _show_login_dialog()
            st.stop()

        sel_state   = st.session_state.get("find_tbl", {})
        edited_rows = sel_state.get("edited_rows", {})
        sel_indices = [int(i) for i, v in edited_rows.items() if v.get("✓")]

        if st.session_state.select_all or not sel_indices:
            to_enrich = st.session_state.search_results
        else:
            to_enrich = [st.session_state.search_results[i] for i in sel_indices]

        with st.spinner(f"Enriching {len(to_enrich)} contacts (uses Apollo credits)..."):
            enriched = _enrich_people(to_enrich)
        st.session_state.enriched_results = enriched

        if enriched:
            with st.spinner("Saving to hr_contacts..."):
                saved = _save_contacts(enriched)
            with_email = [p for p in enriched if p.get("email")]
            st.success(
                f"✅ {len(enriched)} enriched · {len(with_email)} have emails"
                + (f" · {saved} saved to DB" if saved else " · (DB save failed — check Supabase config)")
            )

    # ── Display results ──────────────────────────────────────────────────────

    results  = st.session_state.search_results
    enriched = st.session_state.enriched_results

    if results:
        s1, s2, s3 = st.columns(3)
        for col, num, lbl in [
            (s1, len(results),  "Found"),
            (s2, len(enriched), "Enriched"),
            (s3, len([p for p in enriched if p.get("email")]), "With Email"),
        ]:
            col.markdown(
                f'<div class="stat"><div class="stat-n">{num}</div>'
                f'<div class="stat-l">{lbl}</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # Search results table
        def _obf(last):
            s = (last or "").strip().title()
            return (s[0] + "·" * max(len(s) - 1, 0)) if s else "—"

        df1 = pd.DataFrame([{
            "✓":          st.session_state.select_all,
            "First Name": (p.get("first_name") or "").strip().title() or "—",
            "Last Name":  _obf(p.get("last_name")),
            "Title":      p.get("title") or "—",
            "Company":    ((p.get("organization") or {}).get("name") or "—")
                          if isinstance(p.get("organization"), dict) else "—",
        } for p in results])

        edited = st.data_editor(
            df1,
            use_container_width=True,
            hide_index=True,
            height=380,
            column_config={
                "✓":          st.column_config.CheckboxColumn("", width=40),
                "First Name": st.column_config.TextColumn(width="medium"),
                "Last Name":  st.column_config.TextColumn(width="small"),
                "Title":      st.column_config.TextColumn(width="large"),
                "Company":    st.column_config.TextColumn(width="medium"),
            },
            disabled=["First Name", "Last Name", "Title", "Company"],
            key="find_tbl",
        )
        n_sel = int(edited["✓"].sum())
        color = "#8486e0" if n_sel else "#3a3f55"
        hint  = f"✓ {n_sel} selected" if n_sel else f"{len(df1)} results"
        st.markdown(
            f'<p style="color:{color};font-size:0.72rem;margin-top:0.15rem;">{hint}</p>',
            unsafe_allow_html=True,
        )

        # Enriched results table
        if enriched:
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            st.markdown('<p class="sec">Enriched contacts</p>', unsafe_allow_html=True)

            df2 = pd.DataFrame([{
                "Name":     (p.get("name") or "").strip().title() or "—",
                "Title":    p.get("title") or "—",
                "Email":    p.get("email") or "—",
                "Company":  ((p.get("organization") or {}).get("name") or "—")
                            if isinstance(p.get("organization"), dict) else "—",
                "LinkedIn": p.get("linkedin_url") or "—",
                "City":     p.get("city") or "—",
            } for p in enriched])

            st.dataframe(
                df2,
                use_container_width=True,
                hide_index=True,
                height=380,
                column_config={
                    "Email":    st.column_config.TextColumn(width="large"),
                    "LinkedIn": st.column_config.LinkColumn("LinkedIn", display_text="↗", width="small"),
                },
            )

            valid = [p for p in enriched if p.get("email")]
            dl1, dl2, _ = st.columns([1, 1, 5])
            with dl1:
                st.download_button(
                    "↓ CSV", df2.to_csv(index=False).encode(), "enriched.csv", mime="text/csv"
                )
            with dl2:
                if valid and st.button("📧 Queue for Sending", type="primary", key="queue_btn"):
                    st.session_state.send_contacts = valid
                    st.success(f"✅ {len(valid)} contacts queued — go to the Send tab")
    else:
        st.markdown(
            '<p style="color:#3a3f55;text-align:center;padding:4rem 0;font-size:0.85rem;">'
            'Use the Company Lookup above to find Org IDs, then hit Search</p>',
            unsafe_allow_html=True,
        )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — SEND EMAILS
# ═════════════════════════════════════════════════════════════════════════════

with tab_send:

    if not gmail_ok():
        st.warning(
            "Gmail is not connected. Go to the **Settings** tab to connect your Gmail account.",
            icon="⚠️",
        )

    # ── Reload config on each render ─────────────────────────────────────────
    send_sender   = _cfg("SENDER_NAME", "")
    send_resume   = _cfg("RESUME_URL", "")
    send_linkedin = _cfg("LINKEDIN_URL", "")
    send_website  = _cfg("WEBSITE_URL", "")
    send_tracking = _cfg("TRACKING_URL", _SB_FN_BASE)

    # ── Email configuration ──────────────────────────────────────────────────
    st.markdown('<p class="sec">Email configuration</p>', unsafe_allow_html=True)

    cfg1, cfg2 = st.columns([3, 2])
    with cfg1:
        subject_tpl = st.text_input(
            "Subject line",
            value=DEFAULT_SUBJECT.replace("{sender_name}", send_sender or "{sender_name}"),
            key="send_subject",
        )
    with cfg2:
        if send_sender:
            st.markdown(
                f'<p style="color:#4b5270;font-size:0.78rem;padding-top:2rem;">'
                f'Sending as &nbsp;<strong style="color:#e2e4ed;">{send_sender}</strong>'
                f'</p>',
                unsafe_allow_html=True,
            )
        else:
            st.warning("Set your name in Settings.", icon="ℹ️")

    # ── Template editor ──────────────────────────────────────────────────────
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<p class="sec">Email template</p>', unsafe_allow_html=True)
    st.caption(
        "Variables: `{first_name}`, `{company}`, `{sender_name}`, "
        "`{resume_link}`, `{linkedin_link}`, `{website_link}`. "
        "Tracking pixel is added automatically."
    )

    template = st.text_area(
        "HTML template",
        value=st.session_state.email_template,
        height=300,
        key="send_template",
        label_visibility="collapsed",
    )
    st.session_state.email_template = template

    # ── Contacts queue ───────────────────────────────────────────────────────
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<p class="sec">Contacts to email</p>', unsafe_allow_html=True)

    src_col1, src_col2 = st.columns([2, 2])
    with src_col1:
        src = st.radio(
            "Contact source",
            ["Queued from Find tab", "Load from Supabase DB"],
            horizontal=True,
            key="send_src",
            label_visibility="collapsed",
        )
    with src_col2:
        if st.button("↻ Refresh contacts", key="refresh_contacts"):
            st.rerun()

    # Load contacts based on source
    if src == "Queued from Find tab":
        raw_contacts = st.session_state.send_contacts
        if not raw_contacts:
            st.info("No contacts queued. Go to Find tab → Enrich contacts → click 'Queue for Sending'.")
    else:
        # Load from hr_contacts, optionally excluding already emailed
        show_all = st.checkbox("Include already-emailed contacts", value=False, key="send_show_all")
        with st.spinner("Loading contacts from Supabase..."):
            all_contacts_raw = sb_get(
                "hr_contacts",
                "email=not.is.null&select=*&order=created_at.desc&limit=200",
            )
            already_emailed  = {
                r.get("recipient_email")
                for r in sb_get("email_sends", "select=recipient_email")
            }
        if show_all:
            raw_contacts = [c for c in all_contacts_raw if c.get("email")]
        else:
            raw_contacts = [
                c for c in all_contacts_raw
                if c.get("email") and c.get("email") not in already_emailed
            ]
        if not raw_contacts:
            if show_all:
                st.info("No contacts with emails in DB. Use the Find tab to search and enrich contacts first.")
            else:
                st.info("All contacts have already been emailed. Check 'Include already-emailed contacts' to resend.")

    if raw_contacts:
        send_df = pd.DataFrame([{
            "✓":      False,
            "Name":   (c.get("name") or c.get("first_name") or "").strip().title() or "—",
            "Email":  c.get("email") or "—",
            "Company": c.get("company") or "—",
            "Title":  c.get("title") or "—",
        } for c in raw_contacts])

        sa1, sa2, _ = st.columns([1, 1, 6])
        with sa1:
            if st.button("Select All", key="send_selall"):
                send_df["✓"] = True
        with sa2:
            if st.button("Clear", key="send_clear"):
                send_df["✓"] = False

        edited_send = st.data_editor(
            send_df,
            use_container_width=True,
            hide_index=True,
            height=360,
            column_config={
                "✓":       st.column_config.CheckboxColumn("", width=40),
                "Name":    st.column_config.TextColumn(width="medium"),
                "Email":   st.column_config.TextColumn(width="large"),
                "Company": st.column_config.TextColumn(width="medium"),
                "Title":   st.column_config.TextColumn(width="large"),
            },
            disabled=["Name", "Email", "Company", "Title"],
            key="send_tbl",
        )

        selected_indices = [i for i, row in edited_send.iterrows() if row["✓"]]
        selected_contacts = [raw_contacts[i] for i in selected_indices]
        n_sel = len(selected_contacts)

        st.markdown(
            f'<p style="color:{"#8486e0" if n_sel else "#3a3f55"};font-size:0.72rem;margin-top:0.15rem;">'
            f'{"✓ " + str(n_sel) + " selected" if n_sel else str(len(send_df)) + " contacts available"}'
            f'</p>',
            unsafe_allow_html=True,
        )

        # ── Preview + Send / Schedule buttons ────────────────────────────────
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown('<p class="sec">Send options</p>', unsafe_allow_html=True)

        send_mode = st.radio(
            "Send mode",
            ["Send now", "Schedule for later"],
            horizontal=True,
            key="send_mode",
            label_visibility="collapsed",
        )

        scheduled_at_cdt = None
        if send_mode == "Schedule for later":
            sch1, sch2 = st.columns([1, 1])
            with sch1:
                sch_date = st.date_input(
                    "Date (CDT)",
                    value=datetime.now(CDT).date(),
                    key="sch_date",
                )
            with sch2:
                sch_time = st.time_input(
                    "Time (CDT)",
                    value=datetime.now(CDT).replace(hour=9, minute=0, second=0, microsecond=0).time(),
                    key="sch_time",
                    step=300,
                )
            scheduled_at_cdt = datetime(
                sch_date.year, sch_date.month, sch_date.day,
                sch_time.hour, sch_time.minute, tzinfo=CDT,
            )
            st.caption(f"📅 Will be stored as scheduled for {scheduled_at_cdt.strftime('%b %d, %Y at %I:%M %p CDT')}")

        pa, pb, _ = st.columns([1, 2, 4])

        with pa:
            preview_btn = st.button("Preview email", key="preview_btn", disabled=not selected_contacts)

        with pb:
            if send_mode == "Send now":
                send_label = f"🚀 Send {n_sel} email{'s' if n_sel != 1 else ''}" if n_sel else "Send emails"
                send_all_btn = st.button(
                    send_label,
                    type="primary",
                    use_container_width=True,
                    key="send_all_btn",
                    disabled=not selected_contacts or not gmail_ok(),
                )
                schedule_btn = False
            else:
                send_all_btn = False
                schedule_label = f"📅 Schedule {n_sel} email{'s' if n_sel != 1 else ''}" if n_sel else "Schedule emails"
                schedule_btn = st.button(
                    schedule_label,
                    type="primary",
                    use_container_width=True,
                    key="schedule_btn",
                    disabled=not selected_contacts or not SB_URL,
                )

        # Preview
        if preview_btn and selected_contacts:
            c = selected_contacts[0]
            first = (c.get("first_name") or c.get("name") or "").strip().title().split()[0] if c.get("name") or c.get("first_name") else "there"
            company = c.get("company") or "your company"
            preview_id = "preview-tracking-id"
            preview_html = build_email_html(
                template, first, company, preview_id,
                send_sender, send_resume, send_linkedin, send_website, send_tracking,
            )
            with st.expander(f"Preview — {c.get('name', '')} at {company}", expanded=True):
                st.markdown(
                    f'<div style="background:#0f1117;border:1px solid #1e2130;border-radius:8px;padding:1.5rem;">'
                    f'{preview_html}</div>',
                    unsafe_allow_html=True,
                )

        # Send
        if send_all_btn and selected_contacts and gmail_ok():
            progress = st.progress(0, text="Sending emails...")
            sent_ok, sent_fail = 0, []
            total = len(selected_contacts)

            for idx, c in enumerate(selected_contacts):
                first_name = (c.get("first_name") or "").strip().title() or (
                    (c.get("name") or "").strip().title().split()[0]
                )
                company    = c.get("company") or ""
                to_email   = c.get("email", "")
                full_name  = (c.get("name") or "").strip().title() or first_name

                if not to_email:
                    sent_fail.append(f"{full_name} — no email")
                    continue

                email_id = str(uuid.uuid4())

                # Build HTML
                html = build_email_html(
                    template, first_name, company, email_id,
                    send_sender, send_resume, send_linkedin, send_website, send_tracking,
                )

                # Build subject
                subject = subject_tpl.replace("{first_name}", first_name).replace("{company}", company)

                # Insert tracking record BEFORE sending (so pixel works immediately)
                tracking_row = {
                    "email_id":         email_id,
                    "name":             full_name,
                    "company":          company,
                    "recipient_email":  to_email,
                    "subject":          subject,
                    "sent_at":          datetime.now(CDT).isoformat(),
                    "email_opened":     False,
                    "email_opened_count": 0,
                    "resume_opened":    False,
                    "linkedin_opened":  False,
                    "website_opened":   False,
                }
                sb_insert("email_sends", tracking_row)

                # Send via Gmail
                try:
                    gmail_send(to_email, subject, html)
                    sent_ok += 1
                except Exception as e:
                    sent_fail.append(f"{full_name} <{to_email}> — {e}")

                progress.progress(
                    (idx + 1) / total,
                    text=f"Sending {idx + 1}/{total} — {full_name}...",
                )
                time.sleep(0.3)  # gentle rate limiting

            progress.empty()

            if sent_ok:
                st.success(f"✅ {sent_ok} email{'s' if sent_ok != 1 else ''} sent successfully!")
            if sent_fail:
                st.error(f"⚠️ {len(sent_fail)} failed:")
                for f in sent_fail:
                    st.caption(f"  • {f}")

        # ── Schedule emails ───────────────────────────────────────────────────
        if schedule_btn and selected_contacts and scheduled_at_cdt:
            sch_ok, sch_fail = 0, []
            for c in selected_contacts:
                first_name = (c.get("first_name") or "").strip().title() or (
                    (c.get("name") or "").strip().title().split()[0]
                )
                company   = c.get("company") or ""
                to_email  = c.get("email", "")
                full_name = (c.get("name") or "").strip().title() or first_name

                if not to_email:
                    sch_fail.append(f"{full_name} — no email")
                    continue

                email_id = str(uuid.uuid4())
                subject  = subject_tpl.replace("{first_name}", first_name).replace("{company}", company)
                html     = build_email_html(
                    template, first_name, company, email_id,
                    send_sender, send_resume, send_linkedin, send_website, send_tracking,
                )

                row = {
                    "email_id":           email_id,
                    "name":               full_name,
                    "company":            company,
                    "recipient_email":    to_email,
                    "subject":            subject,
                    "email_body":         html,
                    "status":             "scheduled",
                    "scheduled_at":       scheduled_at_cdt.isoformat(),
                    "sent_at":            None,
                    "email_opened":       False,
                    "email_opened_count": 0,
                    "resume_opened":      False,
                    "linkedin_opened":    False,
                    "website_opened":     False,
                }
                result = sb_insert("email_sends", row)
                if result:
                    sch_ok += 1
                else:
                    sch_fail.append(f"{full_name} — DB error")

            if sch_ok:
                st.success(f"📅 {sch_ok} email{'s' if sch_ok != 1 else ''} scheduled for {scheduled_at_cdt.strftime('%b %d at %I:%M %p CDT')}!")
            if sch_fail:
                st.error(f"⚠️ {len(sch_fail)} failed:")
                for f in sch_fail:
                    st.caption(f"  • {f}")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════

with tab_dash:

    # ── Fetch data ───────────────────────────────────────────────────────────
    def _fetch_tracking() -> tuple[list | None, str | None]:
        if not SB_URL or not SB_KEY:
            return None, "Supabase credentials missing — check Settings."
        try:
            r = req.get(
                f"{SB_URL}/rest/v1/email_sends?select=*&order=sent_at.desc",
                headers={"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"},
                timeout=10,
            )
            if r.status_code == 200:
                return r.json(), None
            return None, f"Error {r.status_code}: {r.text}"
        except Exception as e:
            return None, str(e)

    # Load on first render or after refresh
    if "dash_data" not in st.session_state:
        st.session_state.dash_data = None

    dh1, dh2, dh3 = st.columns([6, 1, 2])
    with dh1:
        st.markdown(
            '## Hunt Tracker'
            f'<p style="color:#4b5270;font-size:0.82rem;margin-top:-0.4rem;">'
            f'Internship cold email dashboard &nbsp;·&nbsp; {datetime.now(CDT).strftime("%b %d, %Y")}'
            f'</p>',
            unsafe_allow_html=True,
        )
    with dh2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("↻ Refresh", type="primary", use_container_width=True, key="dash_refresh"):
            data, err = _fetch_tracking()
            if data is not None:
                st.session_state.dash_data = data
            else:
                st.error(err)

    with dh3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📤 Send Scheduled", use_container_width=True, key="send_scheduled_btn"):
            now_cdt = datetime.now(CDT).isoformat()
            try:
                due_r = req.get(
                    f"{SB_URL}/rest/v1/email_sends"
                    f"?select=*&status=eq.scheduled&scheduled_at=lte.{now_cdt}",
                    headers={"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"},
                    timeout=10,
                )
                due = due_r.json() if due_r.status_code == 200 else []
            except Exception:
                due = []

            if not due:
                st.info("No emails due to send right now.")
            else:
                sent_sch, fail_sch = 0, []
                for row in due:
                    try:
                        gmail_send(row["recipient_email"], row["subject"], row.get("email_body", ""))
                        req.patch(
                            f"{SB_URL}/rest/v1/email_sends?email_id=eq.{row['email_id']}",
                            headers={
                                "apikey": SB_KEY,
                                "Authorization": f"Bearer {SB_KEY}",
                                "Content-Type": "application/json",
                                "Prefer": "return=minimal",
                            },
                            json={"status": "sent", "sent_at": datetime.now(CDT).isoformat()},
                            timeout=10,
                        )
                        sent_sch += 1
                    except Exception as e:
                        fail_sch.append(f"{row.get('name', row['recipient_email'])} — {e}")

                st.session_state.dash_data = None  # force refresh
                if sent_sch:
                    st.success(f"✅ Sent {sent_sch} scheduled email{'s' if sent_sch != 1 else ''}!")
                if fail_sch:
                    st.error(f"⚠️ {len(fail_sch)} failed: " + ", ".join(fail_sch))

    if st.session_state.dash_data is None:
        with st.spinner(""):
            data, err = _fetch_tracking()
        if data is not None:
            st.session_state.dash_data = data
        else:
            st.error(f"Could not connect to Supabase — {err}")
            st.session_state.dash_data = []  # avoid re-fetching on every rerun

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Build DataFrame ──────────────────────────────────────────────────────
    df = pd.DataFrame(st.session_state.dash_data)

    if df.empty:
        st.info("No emails sent yet. Use the Send tab to start your campaign.")
    else:

        df["sent_at"]        = pd.to_datetime(df.get("sent_at"), errors="coerce", utc=True)
        df["days_since"]     = (pd.Timestamp.now(tz="America/Chicago") - df["sent_at"]).dt.days
        df["email_opened"]   = df.get("email_opened", False).fillna(False)
        df["resume_opened"]  = df.get("resume_opened", False).fillna(False)
        df["linkedin_opened"]= df.get("linkedin_opened", False).fillna(False)
        df["website_opened"] = df.get("website_opened", False).fillna(False)
        df["email_opened_count"]    = df.get("email_opened_count",    0).fillna(0).astype(int)
        df["resume_opened_count"]   = df.get("resume_opened_count",   0).fillna(0).astype(int)
        df["linkedin_opened_count"] = df.get("linkedin_opened_count", 0).fillna(0).astype(int)
        df["website_opened_count"]  = df.get("website_opened_count",  0).fillna(0).astype(int)
        df["viewed_all"]     = df["resume_opened"] & df["linkedin_opened"] & df["website_opened"]

        if "followup_days" not in st.session_state:
            st.session_state.followup_days = 3
        df["needs_followup"] = (~df["email_opened"]) & (df["days_since"] >= st.session_state.followup_days)

        total      = len(df)
        companies  = df.get("company", pd.Series()).nunique()
        opened     = int(df["email_opened"].sum())
        open_rate  = round(opened / total * 100) if total else 0
        resume_ppl = int(df["resume_opened"].sum())
        website_ppl= int(df["website_opened"].sum())
        linkedin_ppl=int(df["linkedin_opened"].sum())
        resume     = int(df["resume_opened_count"].sum())
        website    = int(df["website_opened_count"].sum())
        linkedin   = int(df["linkedin_opened_count"].sum())
        viewed_all = int(df["viewed_all"].sum())
        followup   = int(df["needs_followup"].sum())

        # ── Metric cards ─────────────────────────────────────────────────────────
        def _card(label, value, sub="", warn=False, muted=False):
            sub_cls = "warn" if warn else ("muted" if muted else "")
            return (
                f'<div class="metric-wrap">'
                f'<div class="metric-label">{label}</div>'
                f'<div class="metric-value">{value}</div>'
                + (f'<div class="metric-sub {sub_cls}">{sub}</div>' if sub else "")
                + "</div>"
            )

        cols = st.columns(8)
        metrics = [
            ("Companies",    companies,  "",                                          False, True),
            ("Sent",         total,      "",                                          False, True),
            ("Opened",       opened,     f"{open_rate}% open rate",                  False, False),
            ("Resume Clicks",resume,     f"{resume_ppl} unique",                     False, resume == 0),
            ("LinkedIn Clicks",linkedin, f"{linkedin_ppl} unique",                   False, linkedin == 0),
            ("Website Clicks",website,   f"{website_ppl} unique",                    False, website == 0),
            ("Viewed All 3", viewed_all, f"{round(viewed_all/total*100)}%" if total else "", False, viewed_all == 0),
            ("Follow-up",    followup,   f">{st.session_state.followup_days}d no open", followup > 0, not followup > 0),
        ]
        for col, (label, val, sub, warn, muted) in zip(cols, metrics):
            col.markdown(_card(label, val, sub, warn, muted), unsafe_allow_html=True)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # ── Charts ───────────────────────────────────────────────────────────────
        ch1, ch2, ch3 = st.columns(3)
        with ch1:
            st.markdown('<p class="sec">Open Rate</p>', unsafe_allow_html=True)
            st.bar_chart(
                pd.DataFrame({"Status": ["Opened", "Not Opened"], "Count": [opened, total - opened]})
                .set_index("Status"),
                color=["#3ecf8e"], height=180,
            )
        with ch2:
            st.markdown('<p class="sec">Link Clicks (total)</p>', unsafe_allow_html=True)
            st.bar_chart(
                pd.DataFrame({
                    "Link":  ["Resume", "LinkedIn", "Website"],
                    "Clicks": [resume, linkedin, website],
                }).set_index("Link"),
                color=["#6366f1"], height=180,
            )
        with ch3:
            st.markdown('<p class="sec">Outreach by Company</p>', unsafe_allow_html=True)
            if "company" in df.columns:
                st.bar_chart(
                    df.groupby("company").size().reset_index(name="Count")
                    .sort_values("Count", ascending=False).head(6).set_index("company"),
                    color=["#f59e0b"], height=180,
                )

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # ── Filters ──────────────────────────────────────────────────────────────
        st.markdown('<p class="sec">Outreach Log</p>', unsafe_allow_html=True)

        ff1, ff2, ff3 = st.columns([2, 2, 1])
        with ff1:
            company_opts   = ["All Companies"] + sorted(df.get("company", pd.Series()).dropna().unique().tolist())
            company_filter = st.selectbox("", company_opts, label_visibility="collapsed", key="dash_co")
        with ff2:
            search = st.text_input("", placeholder="Search name, company, email…", label_visibility="collapsed", key="dash_search")
        with ff3:
            fd = st.number_input(
                "", min_value=1, max_value=14,
                value=st.session_state.followup_days, step=1,
                label_visibility="collapsed",
                help="Follow-up threshold (days)",
                key="dash_fd",
            )
            if fd != st.session_state.followup_days:
                st.session_state.followup_days = fd
                st.rerun()

        # Pill filters
        PILL_FILTERS = [
            ("All", "All"), ("Opened", "Opened"), ("Not Opened", "Not Opened"),
            ("Resume", "Resume"), ("LinkedIn", "LinkedIn"),
            ("Website", "Website"), ("All 3", "Viewed All 3"), ("Follow-up", "Follow-up"),
        ]
        pill_cols = st.columns(len(PILL_FILTERS))
        for col, (key, label) in zip(pill_cols, PILL_FILTERS):
            with col:
                is_active = st.session_state.active_filter == key
                if st.button(
                    f"● {label}" if is_active else label,
                    key=f"dpill_{key}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state.active_filter = key
                    st.rerun()

        # ── Apply filters ─────────────────────────────────────────────────────────
        filtered = df.copy()
        if search:
            m = (
                filtered.get("name",            pd.Series([""] * len(filtered))).fillna("").str.contains(search, case=False) |
                filtered.get("recipient_email", pd.Series([""] * len(filtered))).fillna("").str.contains(search, case=False) |
                filtered.get("company",         pd.Series([""] * len(filtered))).fillna("").str.contains(search, case=False)
            )
            filtered = filtered[m]

        if company_filter != "All Companies":
            filtered = filtered[filtered.get("company", pd.Series()) == company_filter]

        filter_map = {
            "Opened":     lambda f: f[f["email_opened"]],
            "Not Opened": lambda f: f[~f["email_opened"]],
            "Resume":     lambda f: f[f["resume_opened"]],
            "LinkedIn":   lambda f: f[f["linkedin_opened"]],
            "Website":    lambda f: f[f["website_opened"]],
            "All 3":      lambda f: f[f["viewed_all"]],
            "Follow-up":  lambda f: f[f["needs_followup"]],
        }
        active = st.session_state.active_filter
        if active in filter_map:
            filtered = filter_map[active](filtered)

        # ── Table ─────────────────────────────────────────────────────────────────
        def _status(row):
            if row.get("email_opened"):
                return f"Opened ×{int(row.get('email_opened_count', 0))}"
            if row.get("needs_followup"):
                return "Follow-up needed"
            return "Not opened"

        def _clicks(row):
            c = []
            if row.get("resume_opened"):
                n = int(row.get("resume_opened_count") or 0)
                c.append(f"Resume ×{n}" if n > 1 else "Resume")
            if row.get("linkedin_opened"):
                n = int(row.get("linkedin_opened_count") or 0)
                c.append(f"LinkedIn ×{n}" if n > 1 else "LinkedIn")
            if row.get("website_opened"):
                n = int(row.get("website_opened_count") or 0)
                c.append(f"Website ×{n}" if n > 1 else "Website")
            return "  ·  ".join(c) if c else "—"

        display = filtered.copy()
        display["Status"]   = display.apply(_status, axis=1)
        display["Links"]    = display.apply(_clicks, axis=1)
        display["Sent"]     = display["sent_at"].dt.strftime("%b %d")
        display["Days Ago"] = display["days_since"].fillna(0).astype(int).astype(str) + "d"

        show_cols = [c for c in ["name", "company", "recipient_email", "Sent", "Days Ago", "Status", "Links"] if c in display.columns]
        rename_map = {"name": "HR Name", "company": "Company", "recipient_email": "Email"}

        st.dataframe(
            display[show_cols].rename(columns=rename_map),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Email":    st.column_config.TextColumn(width="medium"),
                "Status":   st.column_config.TextColumn(width="medium"),
                "Links":    st.column_config.TextColumn(width="medium"),
                "Sent":     st.column_config.TextColumn(width="small"),
                "Days Ago": st.column_config.TextColumn(width="small"),
            },
        )
        st.markdown(
            f'<p style="color:#4b5270;font-size:0.75rem;margin-top:0.25rem;">'
            f'Showing {len(filtered)} of {total}</p>',
            unsafe_allow_html=True,
        )

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # ── Follow-up section ─────────────────────────────────────────────────────
        followup_df = df[df["needs_followup"]]
        if len(followup_df) > 0:
            st.markdown(
                f'<p class="sec">Follow-up needed &nbsp;·&nbsp; {len(followup_df)} HRs</p>',
                unsafe_allow_html=True,
            )
            for _, row in followup_df.iterrows():
                with st.expander(
                    f"{row.get('name', '—')}  ·  {row.get('company', '—')}  ·  {int(row['days_since'])}d ago"
                ):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Email** &nbsp; {row.get('recipient_email', '—')}")
                        if pd.notna(row.get("sent_at")):
                            st.markdown(f"**Sent** &nbsp;&nbsp;&nbsp; {row['sent_at'].strftime('%B %d, %Y')}")
                    with c2:
                        st.info("Keep it short — 2 lines, reference your original email, reattach resume.")
        else:
            st.markdown(
                '<p style="color:#3ecf8e;font-size:0.85rem;">✓ No follow-ups needed right now</p>',
                unsafe_allow_html=True,
            )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — SETTINGS
# ═════════════════════════════════════════════════════════════════════════════

with tab_settings:

    st.markdown('<p class="sec">Gmail</p>', unsafe_allow_html=True)

    gmail_addr = gmail_sender_addr()
    st.markdown(
        f'<p style="color:#3ecf8e;font-size:0.9rem;">✓ Connected as <strong>{gmail_addr}</strong></p>',
        unsafe_allow_html=True,
    )
    if st.button("Disconnect Gmail", key="gmail_disconnect"):
        if os.path.exists(_TOKEN_FILE):
            os.remove(_TOKEN_FILE)
        st.warning("Disconnected — reload the page to reconnect.")
        st.rerun()

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Personal info ─────────────────────────────────────────────────────────
    st.markdown('<p class="sec">Your Information (used in email templates)</p>', unsafe_allow_html=True)

    sn1, sn2 = st.columns(2)
    with sn1:
        new_sender_name = st.text_input("Your Name", value=_cfg("SENDER_NAME", ""), key="st_sender")
    with sn2:
        new_tracking_url = st.text_input(
            "Tracking Server URL",
            value=_cfg("TRACKING_URL", _SB_FN_BASE),
            help="Supabase Edge Function URL is used by default — works globally for all email recipients.",
            key="st_tracking",
        )

    sl1, sl2, sl3 = st.columns(3)
    with sl1:
        new_resume = st.text_input("Resume URL", value=_cfg("RESUME_URL", ""), key="st_resume",
                                   placeholder="https://...")
    with sl2:
        new_linkedin = st.text_input("LinkedIn URL", value=_cfg("LINKEDIN_URL", ""), key="st_linkedin",
                                     placeholder="https://linkedin.com/in/...")
    with sl3:
        new_website = st.text_input("Portfolio/Website URL", value=_cfg("WEBSITE_URL", ""), key="st_website",
                                    placeholder="https://...")

    if st.button("💾 Save Settings", type="primary", key="save_settings"):
        _save_settings({
            "sender_name":  new_sender_name,
            "tracking_url": new_tracking_url,
            "resume_url":   new_resume,
            "linkedin_url": new_linkedin,
            "website_url":  new_website,
        })
        st.success("✅ Settings saved — they'll take effect on next interaction.")

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── API credentials ───────────────────────────────────────────────────────
    st.markdown('<p class="sec">API Credentials</p>', unsafe_allow_html=True)
    st.caption(
        "These can also be set in a `.env` file or `~/.streamlit/secrets.toml`. "
        "Values saved here are stored in `.app_settings.json` in the app folder."
    )

    cr1, cr2 = st.columns(2)
    with cr1:
        new_apollo = st.text_input("Apollo API Key", value=_cfg("APOLLO_API_KEY", ""), type="password", key="st_apollo")
        new_sb_url = st.text_input("Supabase URL", value=_cfg("SUPABASE_URL", ""), key="st_sburl",
                                   placeholder="https://xxx.supabase.co")
    with cr2:
        new_sb_key = st.text_input("Supabase Anon Key", value=_cfg("SUPABASE_KEY", ""), type="password", key="st_sbkey")

    if st.button("💾 Save Credentials", key="save_creds"):
        _save_settings({
            "apollo_api_key": new_apollo,
            "supabase_url":   new_sb_url,
            "supabase_key":   new_sb_key,
        })
        st.success("✅ Credentials saved.")

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Supabase schema note ──────────────────────────────────────────────────
    st.markdown('<p class="sec">Supabase Tables</p>', unsafe_allow_html=True)
    with st.expander("📋 First-time setup: Run supabase_schema.sql in your Supabase SQL editor"):
        st.markdown(
            "Go to **[supabase.com](https://supabase.com) → Your Project → SQL Editor → New Query**, "
            "then paste and run the contents of `supabase_schema.sql` (included in this project folder). "
            "This creates two fresh tables:"
        )
        st.code(
            """-- TABLE 1: hr_contacts — Apollo HR contacts
CREATE TABLE hr_contacts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  apollo_id       TEXT UNIQUE,
  first_name      TEXT, last_name TEXT, name TEXT,
  title TEXT, headline TEXT, email TEXT, email_status TEXT,
  linkedin_url TEXT, photo_url TEXT, organization_id TEXT,
  company TEXT, city TEXT, state TEXT, country TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- TABLE 2: email_sends — sent emails + open/click tracking
CREATE TABLE email_sends (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email_id            UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
  contact_id          UUID REFERENCES hr_contacts(id) ON DELETE SET NULL,
  name TEXT, company TEXT, recipient_email TEXT NOT NULL, subject TEXT,
  sent_at             TIMESTAMPTZ DEFAULT NOW(),
  email_opened        BOOLEAN DEFAULT FALSE,
  email_opened_count  INT DEFAULT 0,
  last_opened_at      TIMESTAMPTZ,
  resume_opened       BOOLEAN DEFAULT FALSE,
  linkedin_opened     BOOLEAN DEFAULT FALSE,
  website_opened      BOOLEAN DEFAULT FALSE
);""",
            language="sql",
        )
