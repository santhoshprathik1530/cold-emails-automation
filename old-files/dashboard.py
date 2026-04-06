import streamlit as st
import pandas as pd
from datetime import datetime
import requests

st.set_page_config(
    page_title="Hunt Tracker",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

*, body, .stApp {
    font-family: 'Inter', sans-serif !important;
}

.stApp {
    background-color: #080a0f;
}

/* Hide streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; }

/* Metric cards */
.metric-wrap {
    background: #0f1117;
    border: 1px solid #1c1f2e;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    height: 100%;
}
.metric-label {
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #4b5270;
    margin-bottom: 0.5rem;
}
.metric-value {
    font-size: 2rem;
    font-weight: 300;
    color: #e8eaf0;
    line-height: 1;
    margin-bottom: 0.3rem;
}
.metric-sub {
    font-size: 0.75rem;
    color: #3ecf8e;
    font-weight: 500;
}
.metric-sub.warn { color: #f87171; }
.metric-sub.muted { color: #4b5270; }

/* Pill filters */
.pill-row { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1rem; }
.pill {
    display: inline-block;
    padding: 0.35rem 1rem;
    border-radius: 999px;
    border: 1px solid #1c1f2e;
    background: #0f1117;
    color: #4b5270;
    font-size: 0.78rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
    text-decoration: none;
    white-space: nowrap;
}
.pill.active {
    background: #6366f1;
    border-color: #6366f1;
    color: #fff;
}
.pill:hover { border-color: #6366f1; color: #6366f1; }

/* Section label */
.section-label {
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #4b5270;
    font-weight: 600;
    margin-bottom: 1rem;
}

/* Divider */
.div { border: none; border-top: 1px solid #1c1f2e; margin: 1.5rem 0; }

/* Streamlit overrides */
div[data-testid="stMetricValue"] { display: none; }
div[data-testid="stMetric"] { display: none; }

.stDataFrame { border-radius: 12px; overflow: hidden; }
div[data-testid="stDataFrameResizable"] { border: 1px solid #1c1f2e; border-radius: 12px; }

/* Inputs */
div[data-baseweb="input"] input, div[data-baseweb="select"] {
    background: #0f1117 !important;
    border-color: #1c1f2e !important;
    color: #e8eaf0 !important;
    border-radius: 8px !important;
}

/* Buttons */
.stButton > button {
    background: #0f1117;
    border: 1px solid #1c1f2e;
    color: #6b7280;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 500;
    transition: all 0.15s;
}
.stButton > button:hover {
    border-color: #6366f1;
    color: #6366f1;
    background: #0f1117;
}
.stButton > button[kind="primary"] {
    background: #6366f1;
    border-color: #6366f1;
    color: white;
}
.stButton > button[kind="primary"]:hover {
    background: #4f52d4;
    border-color: #4f52d4;
}

/* Expander */
div[data-testid="stExpander"] {
    background: #0f1117;
    border: 1px solid #1c1f2e !important;
    border-radius: 10px;
    margin-bottom: 0.5rem;
}

/* Number input */
div[data-baseweb="input"] { background: #0f1117 !important; }
</style>
""", unsafe_allow_html=True)


# ── SECRETS ───────────────────────────────────────────────────────────────────
SB_URL = st.secrets["supabase_url"]
SB_KEY = st.secrets["supabase_key"]
TABLE  = "email_tracking"


# ── FETCH ─────────────────────────────────────────────────────────────────────
def fetch_supabase():
    try:
        res = requests.get(
            f"{SB_URL}/rest/v1/{TABLE}?select=*&order=sent_at.desc",
            headers={"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"},
            timeout=10
        )
        if res.status_code == 200:
            return res.json(), None
        return None, f"Error {res.status_code}: {res.text}"
    except Exception as e:
        return None, str(e)


# ── SESSION STATE ─────────────────────────────────────────────────────────────
for key, val in {
    "data": None, "source": "",
    "active_filter": "All", "followup_days": 3
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

if st.session_state.data is None:
    with st.spinner(""):
        data, err = fetch_supabase()
    if data is not None:
        st.session_state.data, st.session_state.source = data, "supabase"
    else:
        st.error(f"Could not connect to Supabase — {err}")
        st.stop()


# ── HEADER ────────────────────────────────────────────────────────────────────
c_title, c_refresh = st.columns([8, 1])
with c_title:
    st.markdown("## Hunt Tracker")
    st.markdown(
        f'<p style="color:#4b5270;font-size:0.82rem;margin-top:-0.5rem;">'
        f'Internship cold email dashboard &nbsp;·&nbsp; {datetime.now().strftime("%b %d, %Y")}'
        f'</p>', unsafe_allow_html=True
    )
with c_refresh:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("↻ Refresh", type="primary", use_container_width=True):
        data, err = fetch_supabase()
        if data is not None:
            st.session_state.data, st.session_state.source = data, "supabase"
            st.rerun()
        else:
            st.error(err)

st.markdown('<hr class="div">', unsafe_allow_html=True)


# ── DATAFRAME ─────────────────────────────────────────────────────────────────
df = pd.DataFrame(st.session_state.data)
df["sent_at"]        = pd.to_datetime(df["sent_at"], errors="coerce")
df["days_since"]     = (datetime.now() - df["sent_at"]).dt.days
df["viewed_all"]     = df["resume_opened"] & df["linkedin_opened"] & df["website_opened"]
df["needs_followup"] = (~df["email_opened"]) & (df["days_since"] >= st.session_state.followup_days)

total      = len(df)
companies  = df["company"].nunique()
opened     = int(df["email_opened"].sum())
open_rate  = round(opened / total * 100) if total else 0
resume     = int(df["resume_opened"].sum())
website    = int(df["website_opened"].sum())
linkedin   = int(df["linkedin_opened"].sum())
viewed_all = int(df["viewed_all"].sum())
followup   = int(df["needs_followup"].sum())


# ── METRICS ───────────────────────────────────────────────────────────────────
def card(label, value, sub="", warn=False, muted=False):
    sub_class = "warn" if warn else ("muted" if muted else "")
    return f"""
    <div class="metric-wrap">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {f'<div class="metric-sub {sub_class}">{sub}</div>' if sub else ''}
    </div>"""

cols = st.columns(8)
metrics = [
    ("Companies",    companies,  "",                        False, True),
    ("Emails Sent",  total,      "",                        False, True),
    ("Opened",       opened,     f"{open_rate}% open rate", False, False),
    ("Resume",       resume,     f"{round(resume/total*100)}% of sent" if total else "", False, False),
    ("Website",      website,    f"{round(website/total*100)}% of sent" if total else "", False, False),
    ("LinkedIn",     linkedin,   f"{round(linkedin/total*100)}% of sent" if total else "", False, False),
    ("Viewed All 3", viewed_all, f"{round(viewed_all/total*100)}% of sent" if total else "", False, False),
    ("Follow-up",    followup,   f">{st.session_state.followup_days}d no open", followup > 0, not followup > 0),
]
for col, (label, val, sub, warn, muted) in zip(cols, metrics):
    col.markdown(card(label, val, sub, warn, muted), unsafe_allow_html=True)

st.markdown('<hr class="div">', unsafe_allow_html=True)


# ── CHARTS ────────────────────────────────────────────────────────────────────
ch1, ch2, ch3 = st.columns(3)

with ch1:
    st.markdown('<p class="section-label">Open Rate</p>', unsafe_allow_html=True)
    st.bar_chart(
        pd.DataFrame({"Status": ["Opened", "Not Opened"], "Count": [opened, total - opened]}).set_index("Status"),
        color=["#3ecf8e"], height=180
    )
with ch2:
    st.markdown('<p class="section-label">Link Engagement</p>', unsafe_allow_html=True)
    st.bar_chart(
        pd.DataFrame({"Link": ["Resume", "LinkedIn", "Website", "All 3"], "Count": [resume, linkedin, website, viewed_all]}).set_index("Link"),
        color=["#6366f1"], height=180
    )
with ch3:
    st.markdown('<p class="section-label">Outreach by Company</p>', unsafe_allow_html=True)
    st.bar_chart(
        df.groupby("company").size().reset_index(name="Count")
          .sort_values("Count", ascending=False).head(6).set_index("company"),
        color=["#f59e0b"], height=180
    )

st.markdown('<hr class="div">', unsafe_allow_html=True)


# ── FILTERS ───────────────────────────────────────────────────────────────────
st.markdown('<p class="section-label">Outreach Log</p>', unsafe_allow_html=True)

f1, f2, f3 = st.columns([2, 2, 1])
with f1:
    company_opts   = ["All Companies"] + sorted(df["company"].dropna().unique().tolist())
    company_filter = st.selectbox("", company_opts, label_visibility="collapsed")
with f2:
    search = st.text_input("", placeholder="Search name, company, email…", label_visibility="collapsed")
with f3:
    fd = st.number_input("", min_value=1, max_value=14,
                         value=st.session_state.followup_days, step=1,
                         label_visibility="collapsed",
                         help="Follow-up threshold in days")
    if fd != st.session_state.followup_days:
        st.session_state.followup_days = fd
        st.rerun()

# Pill buttons
FILTERS = [
    ("All",        "All"),
    ("Opened",     "Opened"),
    ("Not Opened", "Not Opened"),
    ("Resume",     "Resume"),
    ("LinkedIn",   "LinkedIn"),
    ("Website",    "Website"),
    ("All 3",      "Viewed All 3"),
    ("Follow-up",  "Follow-up"),
]

pill_cols = st.columns(len(FILTERS))
for col, (key, label) in zip(pill_cols, FILTERS):
    with col:
        is_active = st.session_state.active_filter == key
        btn_label = f"● {label}" if is_active else label
        if st.button(btn_label, key=f"pill_{key}", use_container_width=True,
                     type="primary" if is_active else "secondary"):
            st.session_state.active_filter = key
            st.rerun()

active = st.session_state.active_filter


# ── APPLY FILTERS ─────────────────────────────────────────────────────────────
filtered = df.copy()
if search:
    m = (
        filtered["name"].fillna("").str.contains(search, case=False) |
        filtered["recipient_email"].fillna("").str.contains(search, case=False) |
        filtered["company"].fillna("").str.contains(search, case=False)
    )
    filtered = filtered[m]

if company_filter != "All Companies":
    filtered = filtered[filtered["company"] == company_filter]

filter_map = {
    "Opened":     lambda f: f[f["email_opened"]],
    "Not Opened": lambda f: f[~f["email_opened"]],
    "Resume":     lambda f: f[f["resume_opened"]],
    "LinkedIn":   lambda f: f[f["linkedin_opened"]],
    "Website":    lambda f: f[f["website_opened"]],
    "All 3":      lambda f: f[f["viewed_all"]],
    "Follow-up":  lambda f: f[f["needs_followup"]],
}
if active in filter_map:
    filtered = filter_map[active](filtered)


# ── TABLE ─────────────────────────────────────────────────────────────────────
def status(row):
    if row["email_opened"]:   return f"Opened  ×{int(row['email_opened_count'])}"
    if row["needs_followup"]: return "Follow-up needed"
    return "Not opened"

def clicks(row):
    c = []
    if row.get("resume_opened"):   c.append("Resume")
    if row.get("linkedin_opened"): c.append("LinkedIn")
    if row.get("website_opened"):  c.append("Website")
    return "  ·  ".join(c) if c else "—"

display = filtered.copy()
display["Status"]   = display.apply(status, axis=1)
display["Links"]    = display.apply(clicks, axis=1)
display["Sent"]     = display["sent_at"].dt.strftime("%b %d")
display["Days Ago"] = display["days_since"].astype(int).astype(str) + "d"

st.dataframe(
    display[["name", "company", "recipient_email", "Sent", "Days Ago", "Status", "Links"]]
        .rename(columns={"name": "HR Name", "company": "Company", "recipient_email": "Email"}),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Email":    st.column_config.TextColumn(width="medium"),
        "Status":   st.column_config.TextColumn(width="medium"),
        "Links":    st.column_config.TextColumn(width="medium"),
        "Sent":     st.column_config.TextColumn(width="small"),
        "Days Ago": st.column_config.TextColumn(width="small"),
    }
)
st.markdown(
    f'<p style="color:#4b5270;font-size:0.75rem;margin-top:0.25rem;">'
    f'Showing {len(filtered)} of {total}</p>',
    unsafe_allow_html=True
)


# ── FOLLOW-UP ─────────────────────────────────────────────────────────────────
st.markdown('<hr class="div">', unsafe_allow_html=True)
followup_df = df[df["needs_followup"]]

if len(followup_df) > 0:
    st.markdown(
        f'<p class="section-label">Follow-up needed &nbsp;·&nbsp; {len(followup_df)} HRs</p>',
        unsafe_allow_html=True
    )
    for _, row in followup_df.iterrows():
        with st.expander(f"{row.get('name','—')}  ·  {row.get('company','—')}  ·  {int(row['days_since'])}d ago"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Email** &nbsp; {row['recipient_email']}")
                st.markdown(f"**Sent** &nbsp;&nbsp;&nbsp; {row['sent_at'].strftime('%B %d, %Y')}")
            with c2:
                st.info("Keep it short — 2 lines, reference your original email, name a role, reattach resume.")
else:
    st.markdown(
        '<p style="color:#3ecf8e;font-size:0.85rem;">✓ No follow-ups needed right now</p>',
        unsafe_allow_html=True
    )
