-- ============================================================================
-- GEO AI Platform — P2 Schema Additions
-- Channel API Config, Batch Jobs, Alerts, Client Portal, Performance Indexes
-- ============================================================================

-- ══════════════════════════════════════════════════════════════════
-- P2: Performance Indexes (optimize existing queries)
-- ══════════════════════════════════════════════════════════════════

CREATE INDEX IF NOT EXISTS idx_content_drafts_status ON content_drafts(customer_id, status);
CREATE INDEX IF NOT EXISTS idx_publish_schedules_status ON publish_schedules(customer_id, status, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_detection_results_model ON detection_results(customer_id, model_name, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_optimization_items_priority ON optimization_items(customer_id, priority, status);
CREATE INDEX IF NOT EXISTS idx_weekly_reviews_customer_date ON weekly_reviews(customer_id, week_start DESC);

-- ══════════════════════════════════════════════════════════════════
-- P2: Alert & Monitoring Tables
-- ══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS alert_records (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID REFERENCES customers(id) ON DELETE CASCADE,
    alert_type      VARCHAR(50) NOT NULL,          -- publish_failed, detection_failed, task_missed, negative_sentiment
    severity        VARCHAR(20) NOT NULL DEFAULT 'warning',  -- info, warning, critical
    title           VARCHAR(300) NOT NULL,
    description     TEXT,
    resource_type   VARCHAR(50),
    resource_id     UUID,
    is_resolved     BOOLEAN NOT NULL DEFAULT false,
    resolved_by     UUID REFERENCES users(id),
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_alert_records_customer ON alert_records(customer_id, is_resolved, created_at DESC);

-- ══════════════════════════════════════════════════════════════════
-- P2: Client Portal Accounts
-- ══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS client_accounts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    email           VARCHAR(320) NOT NULL,
    display_name    VARCHAR(200) NOT NULL,
    access_token    VARCHAR(256) NOT NULL UNIQUE,
    token_expires   TIMESTAMPTZ,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    permissions     JSONB NOT NULL DEFAULT '["view_dashboard","view_reports","review_content"]',
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(customer_id, email)
);

-- ══════════════════════════════════════════════════════════════════
-- P2: Batch Job Tracking
-- ══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS batch_jobs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    job_type        VARCHAR(50) NOT NULL,          -- import_kb, export_data, bulk_review, bulk_publish
    status          VARCHAR(30) NOT NULL DEFAULT 'pending',
    total_items     INTEGER NOT NULL DEFAULT 0,
    processed_items INTEGER NOT NULL DEFAULT 0,
    error_items     INTEGER NOT NULL DEFAULT 0,
    result_data     JSONB,
    error_log       JSONB,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

-- ══════════════════════════════════════════════════════════════════
-- P2: New Permissions
-- ══════════════════════════════════════════════════════════════════

INSERT INTO permissions (code, resource, action, description) VALUES
('publish:auto',     'publish',  'auto',    'Auto-publish to API channels'),
('batch:import',     'batch',    'import',  'Batch import KB assets'),
('batch:export',     'batch',    'export',  'Export data to Excel/PDF'),
('monitor:read',     'monitor',  'read',    'View system monitoring')
ON CONFLICT (code) DO NOTHING;

-- Grant to super_admin
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.code = 'super_admin' AND r.customer_id IS NULL AND p.resource IN ('publish', 'batch', 'monitor')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Grant to admin (exclude publish:auto if desired, but include for now)
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.code = 'admin' AND r.customer_id IS NULL AND p.resource IN ('batch', 'monitor')
ON CONFLICT (role_id, permission_id) DO NOTHING;
