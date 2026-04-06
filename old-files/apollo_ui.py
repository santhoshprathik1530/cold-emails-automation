import streamlit as st
import requests
import pandas as pd
import math

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Apollo HR Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── STYLES ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

*, body, .stApp { font-family: 'Inter', sans-serif !important; }
.stApp { background-color: #08090d; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2.5rem; padding-bottom: 2rem; max-width: 1100px; }

/* inputs */
div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea,
div[data-baseweb="select"] {
    background: #0f1117 !important;
    border-color: #1e2130 !important;
    color: #e2e4ed !important;
    border-radius: 8px !important;
    font-size: 0.875rem !important;
}
div[data-baseweb="tag"] { background: #5a5fcf !important; border-radius: 4px !important; }
input::placeholder { color: #3a3f55 !important; }

/* labels */
label, .stTextInput label, .stMultiSelect label,
.stTextArea label, .stNumberInput label {
    color: #3a3f55 !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}

/* buttons */
.stButton > button {
    background: transparent;
    border: 1px solid #1e2130;
    color: #5a5f7a;
    border-radius: 7px;
    font-size: 0.8rem;
    font-weight: 500;
    padding: 0.45rem 1rem;
    transition: all 0.15s;
}
.stButton > button:hover { border-color: #5a5fcf; color: #8486e0; background: #0f1117; }
.stButton > button[kind="primary"] {
    background: #5a5fcf; border-color: #5a5fcf; color: #fff; font-weight: 600;
}
.stButton > button[kind="primary"]:hover { background: #4a4fbf; border-color: #4a4fbf; }

/* download button */
.stDownloadButton > button {
    background: transparent !important;
    border: 1px solid #1e2130 !important;
    color: #5a5f7a !important;
    border-radius: 7px !important;
    font-size: 0.78rem !important;
}
.stDownloadButton > button:hover {
    border-color: #5a5fcf !important; color: #8486e0 !important;
}

/* table */
.stDataFrame, [data-testid="stDataFrameResizable"] {
    border: 1px solid #1e2130 !important;
    border-radius: 10px !important;
    overflow: hidden;
}

/* divider */
.divider { border: none; border-top: 1px solid #13151f; margin: 1.75rem 0; }

/* stat cards */
.stat { background: #0f1117; border: 1px solid #1e2130; border-radius: 10px;
        padding: 0.9rem 1.2rem; text-align: center; }
.stat-n { font-size: 1.75rem; font-weight: 300; color: #e2e4ed; line-height: 1; }
.stat-l { font-size: 0.65rem; letter-spacing: 0.1em; text-transform: uppercase;
          color: #3a3f55; font-weight: 600; margin-top: 0.35rem; }

/* section titles */
.sec { font-size: 0.68rem; letter-spacing: 0.1em; text-transform: uppercase;
       color: #3a3f55; font-weight: 600; margin-bottom: 0.6rem; }
.tbl-title { font-size: 0.9rem; font-weight: 600; color: #c4c6d6; margin-bottom: 0.5rem; }

/* login card */
.login-wrap {
    max-width: 380px; margin: 6rem auto;
    background: #0f1117; border: 1px solid #1e2130;
    border-radius: 16px; padding: 2.5rem 2rem;
}
.login-title { font-size: 1.3rem; font-weight: 600; color: #e2e4ed;
               margin-bottom: 0.25rem; text-align: center; }
.login-sub { font-size: 0.8rem; color: #3a3f55; text-align: center; margin-bottom: 1.75rem; }

/* role badge */
.badge {
    display: inline-block; padding: 0.2rem 0.65rem;
    border-radius: 999px; font-size: 0.68rem; font-weight: 600;
    letter-spacing: 0.06em; text-transform: uppercase;
}
.badge-admin { background: #1e1f3a; color: #8486e0; }
.badge-user  { background: #101a14; color: #3ecf8e; }

/* alert */
div[data-testid="stAlert"] { border-radius: 8px; font-size: 0.82rem; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
APOLLO_API_KEY = "l8TMBu3V3n6o8aDuENZcNA"

APOLLO_HEADERS = {
    "Content-Type": "application/json",
    "Cache-Control": "no-cache",
    "accept": "application/json",
    "x-api-key": APOLLO_API_KEY,
}

DEFAULT_TITLES = [
    "hr", "talent acquisition", "hiring", "recruiter",
    "recruiting", "recruitment", "resource", "sourcer", "sourcing",
]
ALL_TITLES = DEFAULT_TITLES + [
    "people ops", "people operations", "workforce",
    "staffing", "human resources", "hrbp", "talent partner",
]
DEFAULT_LOCATIONS = ["chicago"]
ALL_LOCATIONS = [
    "chicago", "new york", "los angeles", "houston", "phoenix",
    "philadelphia", "san antonio", "san diego", "dallas", "san jose",
    "austin", "jacksonville", "san francisco", "columbus", "seattle",
    "denver", "boston", "nashville", "atlanta", "miami",
    "united states", "canada", "united kingdom",
]

# ── SESSION STATE ─────────────────────────────────────────────────────────────
defaults = {
    "logged_in": False, "role": None, "username": "",
    "search_results": [], "enriched_results": [],
    "last_query": {}, "select_all": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── AUTH ──────────────────────────────────────────────────────────────────────
def check_credentials(username, password):
    """Returns role string or None."""
    try:
        users = st.secrets.get("users", {})
        for uname, info in users.items():
            if uname == username and info["password"] == password:
                return info["role"]
    except Exception:
        pass
    # fallback: hardcoded for local dev (override via secrets in production)
    if username == "admin" and password == st.secrets.get("admin_password", "admin123"):
        return "admin"
    if username == "user" and password == st.secrets.get("user_password", "user123"):
        return "user"
    return None

# ── LOGIN PAGE ────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    st.markdown('<p class="login-title">Apollo HR Search</p>', unsafe_allow_html=True)
    st.markdown('<p class="login-sub">Sign in to continue</p>', unsafe_allow_html=True)

    uname = st.text_input("Username", key="login_user")
    pwd   = st.text_input("Password", type="password", key="login_pass")
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Sign in", type="primary", use_container_width=True):
        role = check_credentials(uname, pwd)
        if role:
            st.session_state.logged_in = True
            st.session_state.role      = role
            st.session_state.username  = uname
            st.rerun()
        else:
            st.error("Invalid username or password.")

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ── LOGGED IN — HEADER ────────────────────────────────────────────────────────
is_admin = st.session_state.role == "admin"

hc1, hc2 = st.columns([6, 1])
with hc1:
    badge_cls  = "badge-admin" if is_admin else "badge-user"
    badge_text = "Admin" if is_admin else "User"
    st.markdown(
        f'<p style="font-size:1.3rem;font-weight:600;color:#e2e4ed;margin-bottom:0.1rem;">'
        f'Apollo HR Search &nbsp;<span class="badge {badge_cls}">{badge_text}</span></p>'
        f'<p style="color:#3a3f55;font-size:0.8rem;margin-top:0;">Hi, {st.session_state.username}</p>',
        unsafe_allow_html=True
    )
with hc2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Sign out", use_container_width=True):
        for k in defaults:
            st.session_state[k] = defaults[k]
        st.rerun()

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# optional n8n webhook URL (can be set in Streamlit secrets as `n8n_webhook`)
n8n_default = st.secrets.get("n8n_webhook", "") if hasattr(st, 'secrets') else ""
n8n_webhook = st.text_input("n8n Webhook URL (optional)", value=n8n_default, help="Full webhook URL to trigger your local n8n workflow, e.g. http://localhost:5678/webhook/abcd")

# ── API CALLS ─────────────────────────────────────────────────────────────────
def run_search(org_ids, locations, titles, target_count):
    all_people = []
    per_page   = 100
    max_pages  = min(500, math.ceil(target_count / per_page) + 2)
    for org_id in org_ids:
        for location in locations:
            page = 1
            while page <= max_pages:
                res = requests.post(
                    "https://api.apollo.io/api/v1/mixed_people/api_search",
                    headers=APOLLO_HEADERS,
                    json={
                        "organization_ids":     [org_id],
                        "contact_email_status": ["verified"],
                        "person_titles":        titles,
                        "person_locations":     [location],
                        "page":                 page,
                        "per_page":             per_page,
                    }
                )
                if res.status_code != 200:
                    st.error(f"API error ({org_id}, {location}, p{page}): {res.status_code}")
                    break
                people = res.json().get("people", [])
                if not people:
                    break
                all_people.extend(people)
                if len(all_people) >= target_count or len(people) < per_page:
                    break
                page += 1
            if len(all_people) >= target_count:
                break
        if len(all_people) >= target_count:
            break
    return all_people[:target_count]


def run_enrich(people):
    matches = []
    for i in range(0, len(people), 10):
        chunk = people[i:i+10]
        res = requests.post(
            "https://api.apollo.io/api/v1/people/bulk_match",
            headers=APOLLO_HEADERS,
            json={"details": [{"id": p["id"]} for p in chunk]}
        )
        if res.status_code == 200:
            matches.extend(res.json().get("matches", []))
        else:
            st.warning(f"Chunk {i//10+1} failed: {res.status_code}")
    return matches


def save_to_db(people):
    try:
        sb_url = st.secrets["supabase_url"]
        sb_key = st.secrets["supabase_key"]
    except KeyError:
        st.warning("Supabase credentials missing — skipping DB save.")
        return 0

    rows = []
    for p in people:
        org = p.get("organization") or {}
        rows.append({
            "apollo_id":                     p.get("id"),
            "first_name":                    p.get("first_name"),
            "last_name":                     p.get("last_name"),
            "name":                          p.get("name"),
            "title":                         p.get("title"),
            "headline":                      p.get("headline"),
            "email":                         p.get("email"),
            "email_status":                  p.get("email_status"),
            "linkedin_url":                  p.get("linkedin_url"),
            "photo_url":                     p.get("photo_url"),
            "github_url":                    p.get("github_url"),
            "facebook_url":                  p.get("facebook_url"),
            "extrapolated_email_confidence": str(p.get("extrapolated_email_confidence") or ""),
            "organization_id":               p.get("organization_id"),
            "company":                       org.get("name") if isinstance(org, dict) else None,
            "city":                          p.get("city"),
            "state":                         p.get("state"),
            "country":                       p.get("country"),
        })

    res = requests.post(
        f"{sb_url}/rest/v1/apollo_contacts",
        headers={
            "apikey":        sb_key,
            "Authorization": f"Bearer {sb_key}",
            "Content-Type":  "application/json",
            "Prefer":        "resolution=merge-duplicates",
        },
        json=rows,
    )
    if res.status_code in (200, 201):
        return len(rows)
    st.error(f"DB error: {res.status_code} — {res.text}")
    return 0

# ── HELPERS ───────────────────────────────────────────────────────────────────
def obfuscate(last):
    s = (last or "").strip().title()
    return (s[0] + "*" * (len(s) - 1)) if s else "—"

def build_search_df(people, select_all=False):
    rows = []
    for p in people:
        org = p.get("organization") or {}
        rows.append({
            "Select":     select_all,
            "First Name": (p.get("first_name") or "").strip().title() or "—",
            "Last Name":  obfuscate(p.get("last_name")),
            "Title":      p.get("title") or "—",
            "Company":    (org.get("name") or "—") if isinstance(org, dict) else "—",
        })
    return pd.DataFrame(rows, columns=["Select", "First Name", "Last Name", "Title", "Company"])

def build_enriched_df(people):
    rows = []
    for p in people:
        org = p.get("organization") or {}
        rows.append({
            "First Name":   (p.get("first_name") or "").strip().title() or "—",
            "Last Name":    (p.get("last_name")  or "").strip().title() or "—",
            "Name":         (p.get("name")        or "").strip().title() or "—",
            "Title":        p.get("title")         or "—",
            "Headline":     p.get("headline")      or "—",
            "Email":        p.get("email")         or "—",
            "Email Status": p.get("email_status")  or "—",
            "LinkedIn":     p.get("linkedin_url")  or "—",
            "Photo":        p.get("photo_url")     or "—",
            "GitHub":       p.get("github_url")    or "—",
            "Facebook":     p.get("facebook_url")  or "—",
            "Email Conf.":  str(p.get("extrapolated_email_confidence") or "—"),
            "Org ID":       p.get("organization_id") or "—",
            "Company":      (org.get("name") or "—") if isinstance(org, dict) else "—",
            "City":         p.get("city")    or "—",
            "State":        p.get("state")   or "—",
            "Country":      p.get("country") or "—",
        })
    return pd.DataFrame(rows)

# ── FILTERS ───────────────────────────────────────────────────────────────────
fc1, fc2 = st.columns([4, 1])
with fc1:
    org_ids_raw = st.text_input(
        "Org ID(s)",
        placeholder="Comma-separated Apollo org IDs",
    )
with fc2:
    target_count = st.number_input("How many?", min_value=1, max_value=5000, value=40)

lc1, lc2 = st.columns([1, 2])
with lc1:
    locations = st.multiselect("Locations", options=ALL_LOCATIONS, default=DEFAULT_LOCATIONS)
with lc2:
    titles = st.multiselect("Title Keywords", options=ALL_TITLES, default=DEFAULT_TITLES)

st.markdown("<br style='line-height:0.2'>", unsafe_allow_html=True)

# buttons row
b1, b2, b3, b4, b5 = st.columns([1, 1, 1, 1, 3])
with b1:
    search_btn = st.button("Search", type="primary", use_container_width=True)
with b2:
    has_results = len(st.session_state.search_results) > 0
    enrich_btn  = st.button(
        "Enrich",
        disabled=not has_results or not is_admin,
        use_container_width=True,
        help="Admin only — uses Apollo credits" if not is_admin else "Enrich selected (or all) contacts",
        type="primary" if is_admin else "secondary",
    )
with b3:
    sel_all_btn = st.button(
        "Select All",
        disabled=not has_results,
        use_container_width=True,
    )
with b4:
    clear_btn = st.button(
        "Clear All",
        disabled=not has_results,
        use_container_width=True,
    )

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── HANDLE ACTIONS ────────────────────────────────────────────────────────────
if search_btn:
    org_ids = [o.strip() for o in org_ids_raw.split(",") if o.strip()]
    if not org_ids:
        st.error("Enter at least one Org ID.")
    elif not locations:
        st.error("Select at least one location.")
    elif not titles:
        st.error("Select at least one title keyword.")
    else:
        with st.spinner(f"Searching for up to {target_count} people..."):
            results = run_search(org_ids, locations, titles, target_count)
        st.session_state.search_results   = results
        st.session_state.enriched_results = []
        st.session_state.select_all       = False
        st.session_state.last_query = {
            "org_ids": org_ids, "locations": locations, "titles": titles,
        }

if sel_all_btn:
    st.session_state.select_all = True

if clear_btn:
    st.session_state.select_all = False

if enrich_btn and is_admin and st.session_state.search_results:
    sel         = st.session_state.get("search_table", {})
    edited_rows = sel.get("edited_rows", {})
    sel_indices = [int(i) for i, v in edited_rows.items() if v.get("Select")]

    # if select_all was used, enrich everything
    if st.session_state.select_all:
        to_enrich = st.session_state.search_results
    elif sel_indices:
        to_enrich = [st.session_state.search_results[i] for i in sel_indices]
    else:
        to_enrich = st.session_state.search_results

    with st.spinner(f"Enriching {len(to_enrich)} contacts..."):
        enriched = run_enrich(to_enrich)
    st.session_state.enriched_results = enriched

    if enriched:
        with st.spinner("Saving to database..."):
            saved = save_to_db(enriched)
        if saved:
            st.success(f"✅ {saved} contacts saved to `apollo_contacts`.")

# ── RESULTS ───────────────────────────────────────────────────────────────────
results  = st.session_state.search_results
enriched = st.session_state.enriched_results

if results:
    # stats
    with_email = len([p for p in enriched if p.get("email")]) if enriched else 0
    s1, s2, s3, s4 = st.columns(4)
    for col, num, lbl in [
        (s1, len(results),  "Found"),
        (s2, len(enriched), "Enriched"),
        (s3, with_email,    "With Email"),
        (s4, len(st.session_state.last_query.get("org_ids", [])), "Orgs"),
    ]:
        col.markdown(
            f'<div class="stat"><div class="stat-n">{num}</div>'
            f'<div class="stat-l">{lbl}</div></div>',
            unsafe_allow_html=True
        )

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── TABLE 1 ───────────────────────────────────────────────────────────────
    st.markdown('<p class="tbl-title">Search Results</p>', unsafe_allow_html=True)

    df1     = build_search_df(results, select_all=st.session_state.select_all)
    edited  = st.data_editor(
        df1,
        use_container_width=True,
        hide_index=True,
        height=380,
        column_config={
            "Select":     st.column_config.CheckboxColumn("",           width=40),
            "First Name": st.column_config.TextColumn("First Name",     width="medium"),
            "Last Name":  st.column_config.TextColumn("Last Name",      width="small"),
            "Title":      st.column_config.TextColumn("Title",          width="large"),
            "Company":    st.column_config.TextColumn("Company",        width="medium"),
        },
        disabled=["First Name", "Last Name", "Title", "Company"],
        key="search_table",
    )

    n_sel = int(edited["Select"].sum())
    hint  = f"✓ {n_sel} selected" if n_sel else f"{len(df1)} results"
    color = "#8486e0" if n_sel else "#3a3f55"
    st.markdown(
        f'<p style="color:{color};font-size:0.72rem;margin-top:0.2rem;">{hint}</p>',
        unsafe_allow_html=True
    )

    st.download_button(
        "↓ CSV",
        data=df1.drop(columns=["Select"]).to_csv(index=False).encode(),
        file_name="search_results.csv",
        mime="text/csv",
    )
    if st.button("Send to n8n", key="send_search_n8n"):
        if not n8n_webhook:
            st.error("Set the n8n Webhook URL above before sending.")
        else:
            try:
                payload = {"filename": "search_results.csv", "rows": df1.drop(columns=["Select"]).to_dict(orient="records")}
                r = requests.post(n8n_webhook, json=payload, timeout=15)
                r.raise_for_status()
                st.success("Search results sent to n8n")
            except Exception as e:
                st.error(f"Failed to send to n8n: {e}")

    # ── TABLE 2 ───────────────────────────────────────────────────────────────
    if enriched:
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown('<p class="tbl-title">Enriched Results</p>', unsafe_allow_html=True)

        df2 = build_enriched_df(enriched)
        st.dataframe(
            df2,
            use_container_width=True,
            hide_index=True,
            height=380,
            column_config={
                "Email":    st.column_config.TextColumn("Email",    width="large"),
                "Headline": st.column_config.TextColumn("Headline", width="large"),
                "LinkedIn": st.column_config.LinkColumn("LinkedIn", display_text="↗", width="small"),
                "Photo":    st.column_config.ImageColumn("Photo",   width="small"),
                "GitHub":   st.column_config.LinkColumn("GitHub",   display_text="↗", width="small"),
                "Facebook": st.column_config.LinkColumn("Facebook", display_text="↗", width="small"),
            },
        )
        st.download_button(
            "↓ CSV",
            data=df2.to_csv(index=False).encode(),
            file_name="enriched_results.csv",
            mime="text/csv",
        )
        if st.button("Send to n8n", key="send_enriched_n8n"):
            if not n8n_webhook:
                st.error("Set the n8n Webhook URL above before sending.")
            else:
                try:
                    payload = {"filename": "enriched_results.csv", "rows": df2.to_dict(orient="records")}
                    r = requests.post(n8n_webhook, json=payload, timeout=15)
                    r.raise_for_status()
                    st.success("Enriched results sent to n8n")
                except Exception as e:
                    st.error(f"Failed to send to n8n: {e}")

else:
    st.markdown(
        '<p style="color:#3a3f55;text-align:center;padding:4rem 0;font-size:0.88rem;">'
        'Enter filters above and hit <strong style="color:#5a5fcf">Search</strong></p>',
        unsafe_allow_html=True
    )
