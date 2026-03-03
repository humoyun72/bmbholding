-- Migration: add_bot_users
-- Description: BotUser jadvalini yaratish — Telegram bot foydalanuvchilarining
--              tili va faollik vaqtini DB da saqlash uchun.
-- Rollback: DROP TABLE IF EXISTS bot_users;

BEGIN;

CREATE TABLE IF NOT EXISTS bot_users (
    telegram_id  BIGINT       NOT NULL PRIMARY KEY,
    lang         VARCHAR(8)   NOT NULL DEFAULT 'uz',
    first_seen   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_active  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_bot_users_telegram_id ON bot_users (telegram_id);

COMMENT ON TABLE bot_users IS 'Telegram bot foydalanuvchilari — til va faollik ma''lumotlari';
COMMENT ON COLUMN bot_users.telegram_id IS 'Telegram foydalanuvchi ID si';
COMMENT ON COLUMN bot_users.lang        IS 'Tanlangan til kodi: uz | ru | en';
COMMENT ON COLUMN bot_users.first_seen  IS 'Birinchi /start vaqti';
COMMENT ON COLUMN bot_users.last_active IS 'Oxirgi faollik vaqti';

COMMIT;

-- Rollback (zarur bo'lsa ishlatish):
-- BEGIN;
-- DROP TABLE IF EXISTS bot_users;
-- COMMIT;

