-- Enable pgvector extension for embedding storage and similarity search.
-- Run in Supabase SQL Editor: CREATE EXTENSION IF NOT EXISTS vector;

CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- documents
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename    TEXT NOT NULL,
    file_url    TEXT NOT NULL,
    file_type   TEXT NOT NULL CHECK (file_type IN ('pptx', 'pdf', 'docx')),
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'processing', 'done', 'error'))
);

CREATE INDEX IF NOT EXISTS idx_documents_status ON documents (status);
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_at ON documents (uploaded_at DESC);

-- ---------------------------------------------------------------------------
-- analysis_results
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analysis_results (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id   UUID NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    module_number INT NOT NULL,
    module_name   TEXT NOT NULL,
    score         FLOAT,
    confidence    FLOAT,
    findings      JSONB NOT NULL DEFAULT '{}',
    flags         JSONB NOT NULL DEFAULT '[]',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_results_document_id
    ON analysis_results (document_id);
CREATE INDEX IF NOT EXISTS idx_analysis_results_module
    ON analysis_results (document_id, module_number);

-- ---------------------------------------------------------------------------
-- risk_reports
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS risk_reports (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    overall_score       INT NOT NULL CHECK (overall_score >= 0 AND overall_score <= 100),
    risk_level          TEXT NOT NULL CHECK (risk_level IN ('Low', 'Medium', 'High')),
    forgery_probability FLOAT NOT NULL CHECK (forgery_probability >= 0 AND forgery_probability <= 1),
    verdict             TEXT NOT NULL,
    summary             TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_risk_reports_document_id
    ON risk_reports (document_id);
CREATE INDEX IF NOT EXISTS idx_risk_reports_created_at
    ON risk_reports (created_at DESC);

-- ---------------------------------------------------------------------------
-- document_embeddings
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS document_embeddings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    chunk_text  TEXT NOT NULL,
    embedding   VECTOR(1536) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_document_embeddings_document_id
    ON document_embeddings (document_id);

-- Optional: IVFFlat index for approximate nearest-neighbor search (create after data exists)
-- CREATE INDEX IF NOT EXISTS idx_document_embeddings_embedding
--     ON document_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
