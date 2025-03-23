CREATE TABLE IF NOT EXISTS news (
    news_id INTEGER PRIMARY KEY AUTOINCREMENT,
    Title TEXT UNIQUE,
    Author TEXT,
    Publication_Date TEXT,
    Link TEXT NOT NULL,
    base_url TEXT NOT NULL,
    paginated_url TEXT NOT NULL,
    created_time TEXT NOT NULL,
    article TEXT,
    keywords TEXT,
    main_category TEXT,
    summary TEXT,
    InfluentialFactor REAL
);



CREATE TABLE IF NOT EXISTS newsletter (
    newsletter_id INTEGER PRIMARY KEY AUTOINCREMENT,
    newsletter_title TEXT UNIQUE,
    broadcast_date TEXT,
    selected_news_id TEXT,
    edition_number INTEGER,
    introduction TEXT,
    top_news_id INTEGER,
    top_news TEXT,
    html TEXT,
    creation TEXT
);


CREATE TABLE IF NOT EXISTS subscriber_new (
    subscriber_id INTEGER PRIMARY KEY AUTOINCREMENT,
    email               TEXT  UNIQUE,
    creation_time       TEXT,
    update_time         TEXT,
    preferences         TEXT,
    age_range           TEXT,
    gender              TEXT,
    residence_country   TEXT,
    annual_income       TEXT,
    crypto_involvement  TEXT
);



--Create the table to save images used for generating html
CREATE TABLE IF NOT EXISTS images (
    image_id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_name TEXT UNIQUE,
    image_base64 TEXT
);