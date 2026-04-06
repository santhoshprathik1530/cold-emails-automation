-- ─────────────────────────────────────────────────────────────────────────
-- Cold Email Hub — Supabase Migration
-- Run this once in your Supabase project's SQL editor:
-- https://supabase.com/dashboard → Your project → SQL Editor
-- Safe to re-run: all statements use IF NOT EXISTS / IF EXISTS guards
-- ─────────────────────────────────────────────────────────────────────────

-- ── Scheduling support (new columns) ─────────────────────────────────────
ALTER TABLE email_sends
  ADD COLUMN IF NOT EXISTS status        TEXT        DEFAULT 'sent',
  ADD COLUMN IF NOT EXISTS scheduled_at  TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS email_body    TEXT;

-- Backfill: mark all existing rows as 'sent'
UPDATE email_sends
SET status = 'sent'
WHERE status IS NULL;

-- Indexes for scheduled email processing
CREATE INDEX IF NOT EXISTS email_sends_status_idx       ON email_sends (status);
CREATE INDEX IF NOT EXISTS email_sends_scheduled_at_idx ON email_sends (scheduled_at);

-- ─────────────────────────────────────────────────────────────────────────
-- Optional: verify the schema looks right
-- ─────────────────────────────────────────────────────────────────────────
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'email_sends'
-- ORDER BY ordinal_position;
