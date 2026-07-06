-- ============================================================================
-- GEO AI Platform — P4 Schema Additions
-- Channel ecosystem, Multi-LLM config, Agent upgrades, Customer success
-- ============================================================================

-- ══════════════════════════════════════════════════════════════════
-- P4: Channel Recommendation & Scoring
-- ══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS channel_scores (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    channel_id      UUID NOT NULL REFERENCES publish_channels(id) ON DELETE CASCADE,
    effectiveness_score FLOAT NOT NULL DEFAULT 0.0,
    exposure_contribution FLOAT NOT NULL DEFAULT 0.0,
    roi_score       FLOAT NOT NULL DEFAULT 0.0,
    total_publishes INTEGER NOT NULL DEFAULT 0,
    success_rate    FLOAT NOT NULL DEFAULT 0.0,
    last_evaluated  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(customer_id, channel_id)
);

-- ══════════════════════════════════════════════════════════════════
-- P4: LLM Provider Configuration
-- ══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS llm_providers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID REFERENCES customers(id) ON DELETE CASCADE,
    provider        VARCHAR(50) NOT NULL,
    model_name      VARCHAR(100) NOT NULL,
    api_key_encrypted TEXT,
    api_base        VARCHAR(500),
    cost_per_1k_tokens FLOAT NOT NULL DEFAULT 0.01,
    quality_score   FLOAT NOT NULL DEFAULT 0.7,
    priority        INTEGER NOT NULL DEFAULT 5,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    config_json     JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ══════════════════════════════════════════════════════════════════
-- P4: Prompt Template Engine
-- ══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS prompt_templates (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID REFERENCES customers(id) ON DELETE CASCADE,
    name            VARCHAR(200) NOT NULL,
    task_type       VARCHAR(50) NOT NULL,
    model_provider  VARCHAR(50),
    system_prompt   TEXT NOT NULL,
    user_prompt_template TEXT NOT NULL,
    variables       JSONB NOT NULL DEFAULT '[]',
    version         INTEGER NOT NULL DEFAULT 1,
    is_latest       BOOLEAN NOT NULL DEFAULT true,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    ab_test_group   VARCHAR(20),
    performance_score FLOAT,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ══════════════════════════════════════════════════════════════════
-- P4: Customer Health Score
-- ══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS customer_health_scores (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE UNIQUE,
    overall_score   FLOAT NOT NULL DEFAULT 0.0,
    exposure_growth_score FLOAT NOT NULL DEFAULT 0.0,
    asset_completeness_score FLOAT NOT NULL DEFAULT 0.0,
    content_frequency_score FLOAT NOT NULL DEFAULT 0.0,
    quota_usage_score FLOAT NOT NULL DEFAULT 0.0,
    engagement_score FLOAT NOT NULL DEFAULT 0.0,
    risk_flags      JSONB NOT NULL DEFAULT '[]',
    recommendations JSONB NOT NULL DEFAULT '[]',
    last_evaluated  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ══════════════════════════════════════════════════════════════════
-- P4: P4 New Permissions
-- ══════════════════════════════════════════════════════════════════

INSERT INTO permissions (code, resource, action, description) VALUES
('channel:manage',   'channel',  'manage',  'Manage all channel adapters'),
('llm:configure',    'llm',      'configure', 'Configure LLM providers and routing'),
('prompt:manage',    'prompt',   'manage',  'Manage prompt templates'),
('health:view',      'health',   'view',    'View customer health scores'),
('report:generate',  'report',   'generate','Generate and send customer reports')
ON CONFLICT (code) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.code = 'super_admin' AND r.customer_id IS NULL AND p.resource IN ('channel', 'llm', 'prompt', 'health', 'report')
ON CONFLICT (role_id, permission_id) DO NOTHING;
