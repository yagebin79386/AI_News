-- News table
CREATE TABLE IF NOT EXISTS crypto_news (
    news_id SERIAL PRIMARY KEY,
    Title TEXT UNIQUE,
    Author TEXT,
    Publication_Date TEXT,
    Link TEXT NOT NULL,
    base_url TEXT NOT NULL,
    paginated_url TEXT,
    created_time TEXT NOT NULL,
    article TEXT,
    keywords TEXT,
    main_category TEXT,
    summary TEXT,
    InfluentialFactor REAL
);

-- Newsletter table
CREATE TABLE IF NOT EXISTS crypto_newsletter (
    newsletter_id SERIAL PRIMARY KEY,
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

-- Subscriber table
CREATE TABLE IF NOT EXISTS crypto_subscriber (
    subscriber_id SERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    creation_time TEXT,
    update_time TEXT,
    preferences TEXT,
    age_range TEXT,
    gender TEXT,
    residence_country TEXT,
    ai_involement TEXT,
    reason_for_subscribing TEXT
);
