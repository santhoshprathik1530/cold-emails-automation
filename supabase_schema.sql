-- ═══════════════════════════════════════════════════════════════════════════
-- Cold Email Hub — Supabase Schema
-- Run this in: supabase.com → Your Project → SQL Editor → New Query
-- ═══════════════════════════════════════════════════════════════════════════


-- ─────────────────────────────────────────────────────────────────────────
-- TABLE 1: hr_contacts
-- Stores HR contacts discovered via Apollo API.
-- ─────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS hr_contacts (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Apollo identifiers
  apollo_id       TEXT        UNIQUE,          -- Apollo's internal person ID
  organization_id TEXT,                        -- Apollo's org ID

  -- Person info
  first_name      TEXT,
  last_name       TEXT,
  name            TEXT,                        -- full name
  title           TEXT,
  headline        TEXT,

  -- Contact info
  email           TEXT,
  email_status    TEXT,                        -- 'verified', 'guessed', etc.
  linkedin_url    TEXT,
  photo_url       TEXT,

  -- Location
  company         TEXT,
  city            TEXT,
  state           TEXT,
  country         TEXT,

  -- Metadata
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast company/email lookups
CREATE INDEX IF NOT EXISTS hr_contacts_company_idx ON hr_contacts (company);
CREATE INDEX IF NOT EXISTS hr_contacts_email_idx   ON hr_contacts (email);


-- ─────────────────────────────────────────────────────────────────────────
-- TABLE 2: email_sends
-- One row per email sent. Tracks opens and link clicks.
-- ─────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS email_sends (
  id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Tracking identifier embedded in pixel URL — must be unique per send
  email_id            UUID        UNIQUE NOT NULL DEFAULT gen_random_uuid(),

  -- FK to hr_contacts (nullable in case contact was not saved to DB first)
  contact_id          UUID        REFERENCES hr_contacts (id) ON DELETE SET NULL,

  -- Denormalized for easy querying without joins
  name                TEXT,
  company             TEXT,
  recipient_email     TEXT        NOT NULL,
  subject             TEXT,

  -- Scheduling
  status              TEXT        DEFAULT 'sent',      -- 'sent' | 'scheduled'
  scheduled_at        TIMESTAMPTZ,                     -- CDT-aware future send time
  email_body          TEXT,                            -- stored HTML for scheduled sends

  -- When was the email sent (null until actually sent for scheduled emails)
  sent_at             TIMESTAMPTZ,

  -- Email open tracking (updated by tracking pixel server)
  email_opened        BOOLEAN     DEFAULT FALSE,
  email_opened_count  INT         DEFAULT 0,
  last_opened_at      TIMESTAMPTZ,

  -- Link click tracking (updated by redirect tracker)
  resume_opened       BOOLEAN     DEFAULT FALSE,
  linkedin_opened     BOOLEAN     DEFAULT FALSE,
  website_opened      BOOLEAN     DEFAULT FALSE
);

-- Index for fast pixel lookups (hit on every email open)
CREATE UNIQUE INDEX IF NOT EXISTS email_sends_email_id_idx ON email_sends (email_id);

-- Index for dashboard queries
CREATE INDEX IF NOT EXISTS email_sends_sent_at_idx         ON email_sends (sent_at DESC);
CREATE INDEX IF NOT EXISTS email_sends_recipient_email_idx ON email_sends (recipient_email);

-- Index for scheduled email processing
CREATE INDEX IF NOT EXISTS email_sends_status_idx          ON email_sends (status);
CREATE INDEX IF NOT EXISTS email_sends_scheduled_at_idx    ON email_sends (scheduled_at);


-- ─────────────────────────────────────────────────────────────────────────
-- Verify (uncomment to inspect after running)
-- ─────────────────────────────────────────────────────────────────────────

-- SELECT table_name, column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_name IN ('hr_contacts', 'email_sends')
-- ORDER BY table_name, ordinal_position;
