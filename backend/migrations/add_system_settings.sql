-- system_settings jadvali yaratish
CREATE TABLE IF NOT EXISTS system_settings (
    key VARCHAR(128) PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

