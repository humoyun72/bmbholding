-- Migration: Add Jira/Redmine ticket fields to cases table
-- Date: 2026-03-02
-- Description: Adds jira_ticket_id and jira_ticket_url columns to support
--              Jira/Redmine integration ticket tracking

-- Add jira_ticket_id column (stores ticket key like "COMP-123" or "#456")
ALTER TABLE cases
    ADD COLUMN IF NOT EXISTS jira_ticket_id VARCHAR(64) DEFAULT NULL;

-- Add jira_ticket_url column (stores direct link to the ticket)
ALTER TABLE cases
    ADD COLUMN IF NOT EXISTS jira_ticket_url VARCHAR(512) DEFAULT NULL;

-- Add index for faster lookups by ticket ID
CREATE INDEX IF NOT EXISTS ix_cases_jira_ticket_id
    ON cases (jira_ticket_id)
    WHERE jira_ticket_id IS NOT NULL;

-- Verify
-- SELECT column_name, data_type, character_maximum_length
-- FROM information_schema.columns
-- WHERE table_name = 'cases'
-- AND column_name IN ('jira_ticket_id', 'jira_ticket_url');

