CREATE TABLE IF NOT EXISTS offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gmail_message_id TEXT,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    company TEXT,
    category TEXT,
    description TEXT,
    seniority TEXT,
    employment_type TEXT,
    salary_min INTEGER,
    salary_max INTEGER,
    currency TEXT,
    location TEXT,
    remote_type TEXT,
    tech_stack TEXT NOT NULL DEFAULT '[]',
    apply_type TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    filter_reasons TEXT NOT NULL DEFAULT '[]',
    first_seen_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cv_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id INTEGER NOT NULL REFERENCES offers(id),
    generated_at TEXT NOT NULL,
    local_file_path TEXT NOT NULL,
    drive_file_id TEXT,
    drive_web_view_link TEXT,
    bullet_ids_used TEXT NOT NULL DEFAULT '[]',
    llm_model_used TEXT
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id INTEGER NOT NULL REFERENCES offers(id),
    cv_version_id INTEGER REFERENCES cv_versions(id),
    sent_at TEXT NOT NULL,
    method TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT
);
