docker-compose exec db psql -U postgres -d integrity -f /docker-entrypoint-initdb.d/add_notification_prefs.sqldocker-compose exec db psql -U postgres -d integrity -c "ALTER TABLE bot_users ADD COLUMN IF NOT EXISTS notification_prefs JSONB DEFAULT '{\"new_assignment\": true, \"deadline_reminder\": true, \"overdue_alert\": true}'::jsonb;"-- Migration: BotUser jadvaliga notification_prefs ustunini qo'shish
-- Date: 2026-03-06

-- notification_prefs ustuni — JSON formatda bildirishnoma sozlamalari
-- Admin/investigator foydalanuvchilar uchun shaxsiy sozlamalar

ALTER TABLE bot_users
ADD COLUMN IF NOT EXISTS notification_prefs JSONB DEFAULT '{"new_assignment": true, "deadline_reminder": true, "overdue_alert": true}'::jsonb;

-- Index qo'shish (JSONB qidiruvlari uchun)
CREATE INDEX IF NOT EXISTS idx_bot_users_notification_prefs ON bot_users USING gin (notification_prefs);

COMMENT ON COLUMN bot_users.notification_prefs IS 'Bildirishnoma sozlamalari: new_assignment, deadline_reminder, overdue_alert';

