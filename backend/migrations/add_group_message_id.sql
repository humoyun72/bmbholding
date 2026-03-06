-- Migration: Add group_message_id to cases table
-- Date: 2026-03-05
-- Description: Stores Telegram group message ID for in-place message editing

ALTER TABLE cases
    ADD COLUMN IF NOT EXISTS group_message_id BIGINT DEFAULT NULL;

-- Index for quick lookup
CREATE INDEX IF NOT EXISTS ix_cases_group_message_id
    ON cases (group_message_id)
    WHERE group_message_id IS NOT NULL;

