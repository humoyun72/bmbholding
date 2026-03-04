-- Migration: Add uploaded_by_admin to case_attachments
-- Date: 2026-03-04

ALTER TABLE case_attachments
    ADD COLUMN IF NOT EXISTS uploaded_by_admin BOOLEAN NOT NULL DEFAULT FALSE;

-- Existing send-file endpoint attachments: retroactively mark admin uploads
-- (optional: mark all existing attachments uploaded via admin send-file as admin)
-- UPDATE case_attachments SET uploaded_by_admin = TRUE WHERE ... ;

COMMENT ON COLUMN case_attachments.uploaded_by_admin IS 'TRUE = admin yuklagan, FALSE = reporter yuklagan (bot orqali)';

