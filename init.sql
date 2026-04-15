-- SmartInbox – Database Initialization (Neon PostgreSQL)
-- ====================================================
-- Tables are auto-created by SQLAlchemy ORM on startup.
-- This script seeds the admin user and ensures extensions exist.
-- Run manually on Neon: psql $DATABASE_URL < init.sql

-- Extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── admin_logs table (created here as safety net; ORM creates it too) ────────
CREATE TABLE IF NOT EXISTS admin_logs (
    id           UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    admin_id     UUID        NOT NULL,
    admin_email  VARCHAR(255) NOT NULL,
    action       VARCHAR(255) NOT NULL,
    target_type  VARCHAR(100),
    target_id    VARCHAR(255),
    detail       TEXT,
    ip_address   VARCHAR(50),
    timestamp    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_id   ON admin_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_action      ON admin_logs(action);
CREATE INDEX IF NOT EXISTS idx_admin_logs_timestamp   ON admin_logs(timestamp DESC);

-- ─── Seed: default admin user (password: Admin@123) ─────────────────────────
-- bcrypt hash of "Admin@123"  (cost=12)
INSERT INTO users (id, email, username, hashed_password, role, is_active, created_at)
VALUES (
    uuid_generate_v4(),
    'admin@smartinbox.com',
    'SuperAdmin',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    'admin',
    true,
    NOW()
) ON CONFLICT (email) DO NOTHING;
