CREATE TABLE auth_sessions (
    session_id VARCHAR(255) NOT NULL PRIMARY KEY,
    session_data BYTEA NOT NULL,                  -- Use JSONB for PostgreSQL, JSON for MySQL
    expire TIMESTAMP(6) NULL
);

CREATE TABLE auth_transactions (
    transaction_id VARCHAR(22) NOT NULL PRIMARY KEY,
    transaction_data BYTEA NOT NULL,                  -- Use JSONB for PostgreSQL, JSON for MySQL
    expire TIMESTAMP(6) NULL
);

-- Crucial for performance: index the expiration column so your cleanup script runs efficiently
-- Allegedy crucial... Cleanup scripts not implemented yet
-- CREATE INDEX idx_sessions_expire ON auth_sessions (expire);
