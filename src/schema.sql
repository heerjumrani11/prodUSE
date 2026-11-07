-- Drop old tables first so this file can be run again safely.
DROP TABLE IF EXISTS feedback, subscriptions, events, users CASCADE;

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    signup_date DATE NOT NULL,
    platform TEXT NOT NULL,
    country TEXT NOT NULL,
    acquisition_channel TEXT NOT NULL,
    plan TEXT NOT NULL  -- plan at signup, so everyone starts as free
);

CREATE TABLE events (
    event_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (user_id),
    event_name TEXT NOT NULL,
    event_time TIMESTAMP NOT NULL,
    app_version TEXT NOT NULL
);

CREATE TABLE subscriptions (
    subscription_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (user_id),
    plan TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,  -- empty means still subscribed
    status TEXT NOT NULL,
    cancel_reason TEXT
);

CREATE TABLE feedback (
    feedback_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (user_id),
    created_at TIMESTAMP NOT NULL,
    channel TEXT NOT NULL,
    rating INTEGER NOT NULL,
    text TEXT NOT NULL
);

-- Indexes make the common questions run faster.
CREATE INDEX idx_events_user ON events (user_id);
CREATE INDEX idx_events_name_time ON events (event_name, event_time);