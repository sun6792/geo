-- ============================================================================
-- GEO AI Platform — Complete Database Schema
-- 7 domains, 36 tables, multi-tenant with RLS
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- Domain 1: Platform & Tenant (4 tables)
-- ============================================================================

CREATE TABLE customers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(200) NOT NULL,
    slug            VARCHAR(100) NOT NULL UNIQUE,
    owner_email     VARCHAR(320) NOT NULL,
    company_name    VARCHAR(300),
    industry        VARCHAR(100),
    status          VARCHAR(20) NOT NULL DEFAULT 'active',       -- active, suspended, deleted
    subscription_tier VARCHAR(20) NOT NULL DEFAULT 'basic',      -- basic, professional, enterprise
    max_users       INTEGER NOT NULL DEFAULT 5,
    max_kb_assets   INTEGER NOT NULL DEFAULT 500,
    max_content_per_month INTEGER NOT NULL DEFAULT 50,
    settings        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE customer_subscriptions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    plan_name       VARCHAR(50) NOT NULL,
    start_date      DATE NOT NULL,
    end_date        DATE,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    payment_status  VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE customer_api_keys (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    key_name        VARCHAR(100) NOT NULL,
    key_hash        VARCHAR(256) NOT NULL UNIQUE,
    key_prefix      VARCHAR(12) NOT NULL,
    scopes          JSONB NOT NULL DEFAULT '[]',
    expires_at      TIMESTAMPTZ,
    last_used_at    TIMESTAMPTZ,
    created_by      UUID NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at      TIMESTAMPTZ
);

CREATE TABLE customer_settings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    setting_key     VARCHAR(100) NOT NULL,
    setting_value   JSONB NOT NULL,
    updated_by      UUID,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(customer_id, setting_key)
);

-- ============================================================================
-- Domain 2: Account & RBAC (7 tables)
-- ============================================================================

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    email           VARCHAR(320) NOT NULL,
    password_hash   VARCHAR(256) NOT NULL,
    display_name    VARCHAR(100) NOT NULL,
    phone           VARCHAR(30),
    avatar_url      VARCHAR(500),
    is_super_admin  BOOLEAN NOT NULL DEFAULT false,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(customer_id, email)
);

CREATE TABLE roles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID REFERENCES customers(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    code            VARCHAR(50) NOT NULL,
    description     TEXT,
    is_system       BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(customer_id, code)
);

CREATE TABLE permissions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code            VARCHAR(100) NOT NULL UNIQUE,
    resource        VARCHAR(50) NOT NULL,
    action          VARCHAR(50) NOT NULL,
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE role_permissions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_id         UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id   UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(role_id, permission_id)
);

CREATE TABLE user_roles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id         UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    granted_by      UUID REFERENCES users(id),
    granted_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, role_id)
);

CREATE TABLE user_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(256) NOT NULL,
    device_info     VARCHAR(500),
    ip_address      INET,
    expires_at      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at      TIMESTAMPTZ
);

CREATE TABLE login_audit (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id),
    customer_id     UUID REFERENCES customers(id),
    email_attempt   VARCHAR(320) NOT NULL,
    success         BOOLEAN NOT NULL,
    failure_reason  VARCHAR(100),
    ip_address      INET,
    user_agent      VARCHAR(500),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_login_audit_user ON login_audit(user_id, created_at DESC);
CREATE INDEX idx_login_audit_customer ON login_audit(customer_id, created_at DESC);

-- ============================================================================
-- Domain 3: Knowledge Base (7 tables)
-- ============================================================================

CREATE TABLE kb_categories (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    parent_id       UUID REFERENCES kb_categories(id) ON DELETE CASCADE,
    name            VARCHAR(200) NOT NULL,
    slug            VARCHAR(200) NOT NULL,
    description     TEXT,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(customer_id, parent_id, slug)
);

CREATE TABLE kb_assets (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    category_id     UUID REFERENCES kb_categories(id) ON DELETE SET NULL,
    title           VARCHAR(500) NOT NULL,
    slug            VARCHAR(500) NOT NULL,
    asset_type      VARCHAR(30) NOT NULL,              -- basic, marketing, multimodal
    content_type    VARCHAR(30) NOT NULL,              -- text, markdown, pdf, docx, image, video, audio
    content_text    TEXT,
    content_json    JSONB,
    file_path       VARCHAR(1000),
    file_size_bytes BIGINT,
    file_hash       VARCHAR(64),
    source_url      VARCHAR(2000),
    status          VARCHAR(20) NOT NULL DEFAULT 'draft',  -- draft, published, archived
    version         INTEGER NOT NULL DEFAULT 1,
    is_latest       BOOLEAN NOT NULL DEFAULT true,
    tags            JSONB NOT NULL DEFAULT '[]',
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_by      UUID NOT NULL REFERENCES users(id),
    updated_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(customer_id, slug, version)
);

CREATE INDEX idx_kb_assets_customer_type ON kb_assets(customer_id, asset_type);
CREATE INDEX idx_kb_assets_customer_status ON kb_assets(customer_id, status);
CREATE INDEX idx_kb_assets_category ON kb_assets(category_id);
CREATE INDEX idx_kb_assets_tags ON kb_assets USING GIN (tags);

CREATE TABLE kb_embeddings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    asset_id        UUID NOT NULL REFERENCES kb_assets(id) ON DELETE CASCADE,
    asset_version   INTEGER NOT NULL,
    chroma_collection VARCHAR(200) NOT NULL,
    chroma_id       VARCHAR(200) NOT NULL,
    chunk_index     INTEGER NOT NULL DEFAULT 0,
    chunk_text      TEXT NOT NULL,
    embedding_model VARCHAR(100) NOT NULL,
    token_count     INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(customer_id, asset_id, asset_version, chunk_index)
);

CREATE INDEX idx_kb_embeddings_asset ON kb_embeddings(asset_id, asset_version);

CREATE TABLE kb_changelog (
    id              BIGSERIAL PRIMARY KEY,
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    asset_id        UUID NOT NULL REFERENCES kb_assets(id) ON DELETE CASCADE,
    change_type     VARCHAR(20) NOT NULL,
    changed_by      UUID NOT NULL REFERENCES users(id),
    changes_json    JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE kb_asset_relationships (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    source_asset_id UUID NOT NULL REFERENCES kb_assets(id) ON DELETE CASCADE,
    target_asset_id UUID NOT NULL REFERENCES kb_assets(id) ON DELETE CASCADE,
    relation_type   VARCHAR(50) NOT NULL,               -- related_to, derived_from, supersedes
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(source_asset_id, target_asset_id, relation_type)
);

CREATE TABLE kb_import_jobs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    job_type        VARCHAR(30) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    total_items     INTEGER NOT NULL DEFAULT 0,
    processed_items INTEGER NOT NULL DEFAULT 0,
    error_items     INTEGER NOT NULL DEFAULT 0,
    result_summary  JSONB,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

-- ============================================================================
-- Domain 4: Content Creation (5 tables)
-- ============================================================================

CREATE TABLE content_briefs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    content_type    VARCHAR(50) NOT NULL,
    target_audience TEXT,
    target_keywords JSONB NOT NULL DEFAULT '[]',
    tone_style      VARCHAR(100),
    word_count_target INTEGER,
    source_kb_asset_ids UUID[] NOT NULL DEFAULT '{}',
    status          VARCHAR(30) NOT NULL DEFAULT 'draft',
    priority        INTEGER NOT NULL DEFAULT 0,
    due_date        DATE,
    created_by      UUID NOT NULL REFERENCES users(id),
    assigned_to     UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_content_briefs_status ON content_briefs(customer_id, status);
CREATE INDEX idx_content_briefs_source ON content_briefs USING GIN (source_kb_asset_ids);

CREATE TABLE content_generation_runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    brief_id        UUID NOT NULL REFERENCES content_briefs(id) ON DELETE CASCADE,
    status          VARCHAR(30) NOT NULL DEFAULT 'pending',
    model_provider  VARCHAR(50) NOT NULL,
    model_name      VARCHAR(100) NOT NULL,
    prompt_template_version VARCHAR(20),
    prompt_text     TEXT,
    tokens_input    INTEGER,
    tokens_output   INTEGER,
    cost_estimate   NUMERIC(10, 6),
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE content_drafts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    brief_id        UUID NOT NULL REFERENCES content_briefs(id) ON DELETE CASCADE,
    generation_run_id UUID REFERENCES content_generation_runs(id) ON DELETE SET NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    title           VARCHAR(500) NOT NULL,
    body_markdown   TEXT NOT NULL,
    body_json       JSONB,
    seo_metadata    JSONB NOT NULL DEFAULT '{}',
    word_count      INTEGER,
    readability_score NUMERIC(5, 2),
    kb_sources      JSONB NOT NULL DEFAULT '[]',
    status          VARCHAR(30) NOT NULL DEFAULT 'draft',
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_content_drafts_brief ON content_drafts(brief_id, version DESC);

CREATE TABLE content_templates (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID REFERENCES customers(id) ON DELETE CASCADE,
    name            VARCHAR(200) NOT NULL,
    content_type    VARCHAR(50) NOT NULL,
    prompt_template TEXT NOT NULL,
    system_prompt   TEXT,
    output_schema   JSONB,
    variables       JSONB NOT NULL DEFAULT '[]',
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE content_generation_history (
    id              BIGSERIAL PRIMARY KEY,
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    brief_id        UUID NOT NULL REFERENCES content_briefs(id) ON DELETE CASCADE,
    generation_run_id UUID NOT NULL REFERENCES content_generation_runs(id) ON DELETE CASCADE,
    draft_id        UUID REFERENCES content_drafts(id) ON DELETE SET NULL,
    action          VARCHAR(30) NOT NULL,
    actor_id        UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- Domain 5: Review Workflow (5 tables)
-- ============================================================================

CREATE TABLE review_records (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    draft_id        UUID NOT NULL REFERENCES content_drafts(id) ON DELETE CASCADE,
    stage           VARCHAR(30) NOT NULL,               -- internal_review, client_review
    status          VARCHAR(30) NOT NULL DEFAULT 'pending',
    reviewer_id     UUID REFERENCES users(id),
    client_reviewer_email VARCHAR(320),
    client_reviewer_name  VARCHAR(200),
    client_access_token   VARCHAR(256),
    client_token_expires  TIMESTAMPTZ,
    reviewed_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(draft_id, stage)
);

CREATE TABLE review_comments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    review_record_id UUID NOT NULL REFERENCES review_records(id) ON DELETE CASCADE,
    parent_id       UUID REFERENCES review_comments(id) ON DELETE CASCADE,
    comment_text    TEXT NOT NULL,
    comment_type    VARCHAR(30) NOT NULL DEFAULT 'general',
    selection_start INTEGER,
    selection_end   INTEGER,
    selected_text   TEXT,
    is_resolved     BOOLEAN NOT NULL DEFAULT false,
    resolved_by     UUID REFERENCES users(id),
    resolved_at     TIMESTAMPTZ,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE review_approval_chain (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    review_record_id UUID NOT NULL REFERENCES review_records(id) ON DELETE CASCADE,
    action          VARCHAR(20) NOT NULL,
    actor_type      VARCHAR(20) NOT NULL,
    actor_id        UUID REFERENCES users(id),
    actor_email     VARCHAR(320),
    comment         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE review_checklists (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    stage           VARCHAR(30) NOT NULL,
    item_text       VARCHAR(500) NOT NULL,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE review_checklist_results (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    review_record_id UUID NOT NULL REFERENCES review_records(id) ON DELETE CASCADE,
    checklist_id    UUID NOT NULL REFERENCES review_checklists(id) ON DELETE CASCADE,
    is_checked      BOOLEAN NOT NULL DEFAULT false,
    checked_by      UUID REFERENCES users(id),
    checked_at      TIMESTAMPTZ,
    UNIQUE(review_record_id, checklist_id)
);

-- ============================================================================
-- Domain 6: Publishing (5 tables)
-- ============================================================================

CREATE TABLE publish_channels (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    name            VARCHAR(200) NOT NULL,
    channel_type    VARCHAR(50) NOT NULL,
    tier            INTEGER NOT NULL CHECK(tier BETWEEN 1 AND 3),
    platform        VARCHAR(100),
    config_json     JSONB NOT NULL DEFAULT '{}',
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE publish_schedules (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    draft_id        UUID NOT NULL REFERENCES content_drafts(id) ON DELETE CASCADE,
    channel_id      UUID NOT NULL REFERENCES publish_channels(id) ON DELETE CASCADE,
    scheduled_at    TIMESTAMPTZ NOT NULL,
    timezone        VARCHAR(50) NOT NULL DEFAULT 'UTC',
    status          VARCHAR(30) NOT NULL DEFAULT 'scheduled',
    published_at    TIMESTAMPTZ,
    published_url   VARCHAR(2000),
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(draft_id, channel_id)
);

CREATE TABLE publish_records (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    schedule_id     UUID NOT NULL REFERENCES publish_schedules(id) ON DELETE CASCADE,
    draft_id        UUID NOT NULL REFERENCES content_drafts(id) ON DELETE CASCADE,
    channel_id      UUID NOT NULL REFERENCES publish_channels(id) ON DELETE CASCADE,
    publish_status  VARCHAR(30) NOT NULL,
    published_url   VARCHAR(2000),
    response_data   JSONB,
    error_message   TEXT,
    published_by    UUID NOT NULL REFERENCES users(id),
    published_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE publish_performance (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    draft_id        UUID NOT NULL REFERENCES content_drafts(id) ON DELETE CASCADE,
    channel_id      UUID NOT NULL REFERENCES publish_channels(id) ON DELETE CASCADE,
    recorded_at     DATE NOT NULL,
    impressions     INTEGER,
    clicks          INTEGER,
    ctr             NUMERIC(7, 4),
    conversions     INTEGER,
    engagement_rate NUMERIC(7, 4),
    bounce_rate     NUMERIC(7, 4),
    avg_time_on_page_sec INTEGER,
    shares          INTEGER,
    comments_count  INTEGER,
    keyword_rankings JSONB,
    traffic_source  JSONB,
    custom_metrics  JSONB NOT NULL DEFAULT '{}',
    notes           TEXT,
    recorded_by     UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(draft_id, channel_id, recorded_at)
);

CREATE TABLE weekly_reviews (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    week_start      DATE NOT NULL,
    week_end        DATE NOT NULL,
    status          VARCHAR(30) NOT NULL DEFAULT 'pending',
    report_markdown TEXT,
    report_json     JSONB,
    highlights      JSONB,
    recommendations JSONB,
    kb_gap_analysis JSONB,
    content_performance_summary JSONB,
    generated_by    UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(customer_id, week_start)
);

-- ============================================================================
-- Domain 7: System & Audit (4 tables)
-- ============================================================================

CREATE TABLE operation_logs (
    id              BIGSERIAL PRIMARY KEY,
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id),
    action          VARCHAR(100) NOT NULL,
    resource_type   VARCHAR(50) NOT NULL,
    resource_id     UUID,
    details_json    JSONB,
    ip_address      INET,
    user_agent      VARCHAR(500),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_operation_logs_customer ON operation_logs(customer_id, created_at DESC);
CREATE INDEX idx_operation_logs_user ON operation_logs(user_id, created_at DESC);
CREATE INDEX idx_operation_logs_resource ON operation_logs(resource_type, resource_id);

CREATE TABLE scheduled_tasks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    task_type       VARCHAR(100) NOT NULL,
    task_name       VARCHAR(200) NOT NULL,
    cron_expression VARCHAR(100) NOT NULL,
    task_params     JSONB NOT NULL DEFAULT '{}',
    is_active       BOOLEAN NOT NULL DEFAULT true,
    last_run_at     TIMESTAMPTZ,
    last_status     VARCHAR(30),
    next_run_at     TIMESTAMPTZ,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    recipient_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    title           VARCHAR(300) NOT NULL,
    body            TEXT,
    resource_type   VARCHAR(50),
    resource_id     UUID,
    is_read         BOOLEAN NOT NULL DEFAULT false,
    read_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_notifications_recipient ON notifications(recipient_id, is_read, created_at DESC);

CREATE TABLE system_config (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key      VARCHAR(200) NOT NULL UNIQUE,
    config_value    JSONB NOT NULL,
    description     TEXT,
    updated_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- Row-Level Security (RLS) — Safety net for tenant isolation
-- ============================================================================

DO $$
DECLARE
    tbl TEXT;
    tenant_tables TEXT[] := ARRAY[
        'customer_subscriptions', 'customer_api_keys', 'customer_settings',
        'users', 'user_roles',
        'kb_categories', 'kb_assets', 'kb_embeddings', 'kb_changelog',
        'kb_asset_relationships', 'kb_import_jobs',
        'content_briefs', 'content_generation_runs', 'content_drafts',
        'content_templates', 'content_generation_history',
        'review_records', 'review_comments', 'review_approval_chain',
        'review_checklists', 'review_checklist_results',
        'publish_channels', 'publish_schedules', 'publish_records',
        'publish_performance', 'weekly_reviews',
        'operation_logs', 'scheduled_tasks', 'notifications'
    ];
BEGIN
    FOREACH tbl IN ARRAY tenant_tables
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', tbl);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY;', tbl);
        EXECUTE format($pol$
            CREATE POLICY tenant_isolation ON %I
            FOR ALL
            USING (customer_id = current_setting('app.current_customer_id', true)::uuid)
            WITH CHECK (customer_id = current_setting('app.current_customer_id', true)::uuid);
        $pol$, tbl);
    END LOOP;
END $$;
