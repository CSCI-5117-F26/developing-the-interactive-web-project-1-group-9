
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    user_password TEXT NOT NULL,
    bio TEXT,
    is_admin BOOLEAN DEFAULT FALSE NOT NULL,
    user_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200),
    content TEXT NOT NULL,
    likes_count INTEGER DEFAULT 0,
    double_likes_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    post_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE follows (
    follower_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    following_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (follower_id, following_id)
);



CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    likes_count INTEGER DEFAULT 0,
    double_likes_count INTEGER DEFAULT 0,
    comment_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE likes (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, post_id)
);

CREATE TABLE double_likes (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, post_id)
);

CREATE TABLE comment_likes (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    comment_id INTEGER NOT NULL REFERENCES comments(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, comment_id)
);

CREATE TABLE comment_double_likes (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    comment_id INTEGER NOT NULL REFERENCES comments(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, comment_id)
);

CREATE TABLE post_reports (
    id SERIAL PRIMARY KEY,
    reporter_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    report_reason VARCHAR(100),
    report_details TEXT,
    report_status VARCHAR(20),
    report_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pfps (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    image_data BYTEA NOT NULL
);

CREATE TABLE banners (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    image_data BYTEA NOT NULL 
);

--auth0
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