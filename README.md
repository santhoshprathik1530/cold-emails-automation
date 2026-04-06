# Cold Email Automation — Internship Hunt Tracker

An end-to-end system that finds recruiter contacts, sends personalized tracked cold emails directly via the Gmail API, and shows real-time engagement data on a dashboard — built to take the guesswork out of internship hunting.

---

## The Problem

Sending cold emails to recruiters is blind by default. You don't know if anyone opened your email, clicked your resume, or even received it. This system fixes that.

---

## How It Works

```
Apollo API (contact discovery)
        ↓
  Streamlit App (app.py)
        ↓
  ┌─────────────────────────────────────┐
  │  1. Search & import HR contacts     │
  │  2. Generate unique tracking ID     │
  │  3. Log contact to Supabase         │
  │  4. Build personalized HTML email   │
  │  5. Inject tracking links + pixel   │
  │  6. Send via Gmail API directly     │
  └─────────────────────────────────────┘
        ↓
   Supabase DB  ←──  Tracking pixels & link redirects (Edge Functions)
        ↓
  Streamlit Dashboard (same app)
```

Every link in the email (resume, LinkedIn, website) routes through a **Supabase Edge Function** that logs the click and redirects. A 1×1 invisible pixel tracks email opens the same way.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Contact discovery | Apollo API |
| App & dashboard | Streamlit (Python) |
| Email sending | Gmail API (OAuth 2.0, direct) |
| Click & open tracking | Supabase Edge Functions |
| Database | Supabase (PostgreSQL) |

---

## App Tabs

The entire workflow lives in a single Streamlit app (`app.py`):

- **Find Contacts** — search Apollo by role/company/location, preview and import HRs
- **Send Emails** — compose personalized emails with tracking links, send via Gmail API
- **Dashboard** — real-time view of opens, clicks, and follow-up flags
- **Settings** — connect Gmail via OAuth, configure tracking URLs and email templates

**Metrics:** Companies reached · Emails sent · Email opens · Resume views · Website clicks · LinkedIn clicks · Viewed all 3 · Follow-up needed

**Filters:** By company · By status (Opened / Not Opened / Resume / LinkedIn / Website / Viewed All 3 / Follow-up)

**Follow-up list:** Auto-flags HRs who haven't opened your email past a set threshold (default 3 days).

---

## Supabase Table Schema

```sql
CREATE TABLE email_tracking (
  tracking_id      TEXT PRIMARY KEY,
  name             TEXT,
  company          TEXT,
  recipient_email  TEXT,
  sent_at          TIMESTAMPTZ,
  email_opened     BOOLEAN DEFAULT FALSE,
  email_opened_count INT DEFAULT 0,
  resume_opened    BOOLEAN DEFAULT FALSE,
  linkedin_opened  BOOLEAN DEFAULT FALSE,
  website_opened   BOOLEAN DEFAULT FALSE
);
```

Edge Functions update the relevant column when a link is clicked or the pixel fires.

---

## Setup

### 1. Supabase
- Create a project and run `supabase_schema.sql`
- Deploy the `track` Edge Function from `supabase/functions/track/`
- The function handles all tracking events and redirects

### 2. Gmail API
- Go to [console.cloud.google.com](https://console.cloud.google.com) → New project
- Enable the **Gmail API**
- Create **OAuth 2.0 Credentials** → Desktop App → download JSON
- Save it as `gmail_credentials.json` in the project root
- In the app, go to **Settings → Connect Gmail** to complete OAuth

### 3. Apollo API
- Get an API key from [apollo.io](https://apollo.io)
- Add it to your `.env` file

### 4. Install & Run

```bash
pip install -r requirements.txt
```

Create `.env`:
```env
APOLLO_API_KEY=your_apollo_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-publishable-key
```

Create `.streamlit/secrets.toml`:
```toml
supabase_url = "https://your-project.supabase.co"
supabase_key = "your-publishable-key"
```

Run:
```bash
streamlit run app.py
```

---

## Roadmap

- [x] Apollo API integration for contact discovery
- [x] Gmail API integration (direct, no middleware)
- [x] Tracking pixel for email opens
- [x] Click tracking for resume, LinkedIn, website
- [x] Real-time Streamlit dashboard
- [x] Follow-up flagging
- [ ] Automated follow-up email sequences
- [ ] Bulk send with rate limiting

---

## Project Structure

```
cold-emails-automation/
├── app.py                # Unified Streamlit app (find · send · track)
├── gmail_service.py      # Gmail OAuth 2.0 + send helpers
├── requirements.txt      # Python dependencies
├── supabase_schema.sql   # DB schema
├── supabase_migration.sql
├── supabase/
│   └── functions/track/  # Supabase Edge Function for tracking
└── .streamlit/
    └── secrets.toml      # local only — not committed
```

---

*Built by Santhosh Kasam — Analytics, Data Science & AI*
