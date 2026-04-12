-- Email captures from anonymous audit completions.
-- Primary lead-gen table: captures emails at the results page
-- without requiring account creation.

CREATE TABLE IF NOT EXISTS email_captures (
    id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    email       text NOT NULL,
    overall_score   numeric,
    overall_band    text,
    company_name    text,
    industry        text,
    source          text DEFAULT 'results_page',
    created_at  timestamptz DEFAULT now()
);

-- Index for dedup and lookups
CREATE INDEX IF NOT EXISTS idx_email_captures_email ON email_captures (email);
CREATE INDEX IF NOT EXISTS idx_email_captures_created ON email_captures (created_at DESC);

-- RLS: only service role can insert (server-side from Streamlit app)
ALTER TABLE email_captures ENABLE ROW LEVEL SECURITY;
