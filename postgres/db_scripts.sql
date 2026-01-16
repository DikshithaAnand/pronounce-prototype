-- CREATE Schema
CREATE SCHEMA IF NOT EXISTS pronounce;

-- Users Table
CREATE TABLE IF NOT EXISTS pronounce.users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Reading Passages Table
CREATE TABLE IF NOT EXISTS pronounce.reading_passages (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    difficulty_level VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Practice Attempts Table
CREATE TABLE IF NOT EXISTS pronounce.practice_attempts (
    id BIGSERIAL PRIMARY KEY,

    user_id BIGINT NOT NULL,
    passage_id BIGINT NOT NULL,

    wpm INTEGER NOT NULL CHECK (wpm >= 0),
    accuracy_score NUMERIC(5,2) NOT NULL CHECK (accuracy_score BETWEEN 0 AND 100),
    fluency_score NUMERIC(5,2) NOT NULL CHECK (fluency_score BETWEEN 0 AND 100),

    mispronounced_count INTEGER NOT NULL DEFAULT 0 CHECK (mispronounced_count >= 0),
    skipped_count INTEGER NOT NULL DEFAULT 0 CHECK (skipped_count >= 0),
    stutter_count INTEGER NOT NULL DEFAULT 0 CHECK (stutter_count >= 0),

    attempt_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

--Attempt Error Table
CREATE TABLE IF NOT EXISTS pronounce.attempt_errors (
    id BIGSERIAL PRIMARY KEY,

    attempt_id BIGINT NOT NULL,

    word_expected VARCHAR(100),
    word_spoken VARCHAR(100),

    error_type VARCHAR(50) NOT NULL
);
