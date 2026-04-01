# Cold Email Automation — Internship Hunt Tracker

An end-to-end system that sends personalized, tracked cold emails to recruiters and shows real-time engagement data on a dashboard — built to take the guesswork out of internship hunting.

---

## The Problem

Sending cold emails to recruiters is blind by default. You don't know if anyone opened your email, clicked your resume, or even received it. This system fixes that.

---

## How It Works

```
Google Sheets (HR queue)
        ↓
    n8n Workflow
        ↓
  ┌─────────────────────────────────────┐
  │  1. Read contacts from queue sheet  │
  │  2. Generate unique tracking ID     │
  │  3. Log contact to Supabase         │
  │  4. Fetch email template (G Docs)   │
  │  5. Inject tracking links + pixel   │
  │  6. Send via Gmail                  │
  └─────────────────────────────────────┘
        ↓
   Supabase DB  ←──  Tracking pixels & link redirects (Edge Functions)
        ↓
  Streamlit Dashboard
```

Every link in the email (resume, LinkedIn, website) routes through a **Supabase Edge Function** that logs the click and redirects. A 1×1 invisible pixel tracks email opens the same way.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Contact queue | Google Sheets |
| Automation | n8n |
| Email template | Google Docs |
| Email sending | Gmail (via n8n) |
| Click & open tracking | Supabase Edge Functions |
| Database | Supabase (PostgreSQL) |
| Dashboard | Streamlit (Python) |

---

## Dashboard

Real-time view of every HR you've contacted.

**Metrics:** Companies reached · Emails sent · Email opens · Resume views · Website clicks · LinkedIn clicks · Viewed all 3 · Follow-up needed

**Filters:** By company · By status (Opened / Not Opened / Resume / LinkedIn / Website / Viewed All 3 / Follow-up)

**Follow-up list:** Auto-flags HRs who haven't opened your email past a set threshold (default 3 days).

---

## n8n Workflow

The workflow lives in [`n8n/workflow.json`](n8n/workflow.json). Import it into your n8n instance to get started.

**Nodes:**
1. **Manual Trigger** — run on demand *(Apollo API automation coming soon)*
2. **Get rows from Google Sheets** — reads the HR contact queue
3. **Generate Tracking ID** — unique ID per contact (`timestamp_random`)
4. **Execute SQL** — logs contact to Supabase `email_tracking` table
5. **Get Google Doc** — fetches the email template
6. **Merge** — combines template + contact data
7. **Code (JavaScript)** — replaces `<name>`, `<company_name>`, `<resume_url>`, `<linkedin_url>`, `<website_url>` placeholders, appends tracking pixel
8. **Send via Gmail** — fires the personalized email

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
- Create a project and run the schema above
- Deploy four Edge Functions: `email-open`, `resume-open`, `linkedin-open`, `website-open`
- Each function updates the matching row and (for links) redirects to the real URL

### 2. Google Sheets
- Create a sheet with columns: `name`, `company`, `email`
- Add your HR contacts to the queue tab

### 3. Google Docs
- Create your email template using these placeholders:
  `<name>`, `<company_name>`, `<resume_url>`, `<linkedin_url>`, `<website_url>`

### 4. n8n
- Import `n8n/workflow.json`
- Connect your Google Sheets, Google Docs, Gmail, and Supabase (Postgres) credentials

### 5. Dashboard
```bash
pip install streamlit pandas requests
```

Create `.streamlit/secrets.toml`:
```toml
supabase_url = "https://your-project.supabase.co"
supabase_key = "your-publishable-key"
```

Run:
```bash
streamlit run dashboard.py
```

---

## Roadmap

- [x] Manual trigger via n8n
- [x] Tracking pixel for email opens
- [x] Click tracking for resume, LinkedIn, website
- [x] Real-time Streamlit dashboard
- [ ] Apollo API integration for automated contact discovery
- [ ] Auto-trigger workflow from Apollo lead list
- [ ] Follow-up email automation

---

## Project Structure

```
cold-emails-automation/
├── dashboard.py          # Streamlit tracking dashboard
├── requirements.txt      # Python dependencies
├── n8n/
│   └── workflow.json     # n8n automation workflow (importable)
└── .streamlit/
    └── secrets.toml      # local only — not committed
```

---

*Built by Santhosh Kasam — Analytics, Data Science & AI*
