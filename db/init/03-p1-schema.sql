-- ============================================================================
-- GEO AI Platform — P1 Schema Additions
-- Agents 1, 2, 5 + Report Data + Channel Upgrades
-- ============================================================================

-- ══════════════════════════════════════════════════════════════════
-- Agent 1: Detection & Collection (6 tables)
-- ══════════════════════════════════════════════════════════════════

CREATE TABLE detection_tasks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    keywords        JSONB NOT NULL DEFAULT '[]',
    target_models   JSONB NOT NULL DEFAULT '[]',
    competitor_ids  UUID[] NOT NULL DEFAULT '{}',
    schedule_type   VARCHAR(20) NOT NULL DEFAULT 'manual',
    cron_expression VARCHAR(100),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    last_run_at     TIMESTAMPTZ,
    last_status     VARCHAR(30),
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE detection_results (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    task_id         UUID NOT NULL REFERENCES detection_tasks(id) ON DELETE CASCADE,
    model_name      VARCHAR(50) NOT NULL,
    keyword         VARCHAR(500) NOT NULL,
    keyword_type    VARCHAR(30) NOT NULL,
    brand_mentioned BOOLEAN NOT NULL DEFAULT false,
    rank_position   INTEGER,
    recommendation_level VARCHAR(20),
    cited_sources   JSONB NOT NULL DEFAULT '[]',
    exposure_count  INTEGER NOT NULL DEFAULT 0,
    raw_response    TEXT,
    result_metadata JSONB NOT NULL DEFAULT '{}',
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_detection_results_task ON detection_results(task_id, model_name);
CREATE INDEX idx_detection_results_customer ON detection_results(customer_id, detected_at DESC);

CREATE TABLE competitors (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    name            VARCHAR(200) NOT NULL,
    website         VARCHAR(500),
    description     TEXT,
    industry        VARCHAR(100),
    tags            JSONB NOT NULL DEFAULT '[]',
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE source_verifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    source_name     VARCHAR(300) NOT NULL,
    source_url      VARCHAR(2000),
    source_type     VARCHAR(50) NOT NULL,
    field_name      VARCHAR(200) NOT NULL,
    kb_value        TEXT,
    source_value    TEXT,
    is_consistent   BOOLEAN NOT NULL DEFAULT true,
    conflict_level  VARCHAR(20),
    resolution      TEXT,
    verified_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_source_verifications_customer ON source_verifications(customer_id, is_consistent);

CREATE TABLE sentiment_results (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    source_name     VARCHAR(300) NOT NULL,
    source_url      VARCHAR(2000),
    title           VARCHAR(500) NOT NULL,
    content_snippet TEXT,
    sentiment       VARCHAR(20) NOT NULL,
    risk_level      VARCHAR(20),
    is_alert        BOOLEAN NOT NULL DEFAULT false,
    keywords_matched JSONB NOT NULL DEFAULT '[]',
    published_at    TIMESTAMPTZ,
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sentiment_results_customer ON sentiment_results(customer_id, sentiment, detected_at DESC);

-- ══════════════════════════════════════════════════════════════════
-- Agent 2: Diagnosis & Analysis (3 tables)
-- ══════════════════════════════════════════════════════════════════

CREATE TABLE diagnosis_reports (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    title           VARCHAR(300) NOT NULL,
    report_type     VARCHAR(30) NOT NULL,
    model_name      VARCHAR(50),
    diagnosis_period_start DATE NOT NULL,
    diagnosis_period_end   DATE NOT NULL,
    status          VARCHAR(30) NOT NULL DEFAULT 'draft',
    summary         TEXT,
    common_gaps     JSONB NOT NULL DEFAULT '[]',
    platform_gaps   JSONB NOT NULL DEFAULT '[]',
    recommendations JSONB NOT NULL DEFAULT '[]',
    report_json     JSONB NOT NULL DEFAULT '{}',
    generated_by    UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_diagnosis_reports_customer ON diagnosis_reports(customer_id, created_at DESC);

CREATE TABLE five_dim_scores (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    diagnosis_report_id UUID NOT NULL REFERENCES diagnosis_reports(id) ON DELETE CASCADE,
    model_name      VARCHAR(50),
    identity_score  FLOAT NOT NULL DEFAULT 0.0,
    source_score    FLOAT NOT NULL DEFAULT 0.0,
    content_depth_score FLOAT NOT NULL DEFAULT 0.0,
    content_freshness_score FLOAT NOT NULL DEFAULT 0.0,
    cross_validation_score FLOAT NOT NULL DEFAULT 0.0,
    total_score     FLOAT NOT NULL DEFAULT 0.0,
    score_metadata  JSONB NOT NULL DEFAULT '{}',
    scored_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_five_dim_scores_report ON five_dim_scores(diagnosis_report_id);

CREATE TABLE optimization_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    diagnosis_report_id UUID REFERENCES diagnosis_reports(id) ON DELETE SET NULL,
    title           VARCHAR(300) NOT NULL,
    description     TEXT,
    category        VARCHAR(50) NOT NULL,
    priority        VARCHAR(20) NOT NULL DEFAULT 'important',
    status          VARCHAR(30) NOT NULL DEFAULT 'pending',
    target_model    VARCHAR(50),
    linked_content_brief_id UUID,
    assigned_to     UUID REFERENCES users(id),
    due_date        DATE,
    completed_at    TIMESTAMPTZ,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_optimization_items_customer ON optimization_items(customer_id, status, priority);

-- ══════════════════════════════════════════════════════════════════
-- Agent 5: Weekly Review Metrics & GEO Rule Base (2 tables)
-- ══════════════════════════════════════════════════════════════════

CREATE TABLE weekly_review_metrics (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    weekly_review_id UUID NOT NULL REFERENCES weekly_reviews(id) ON DELETE CASCADE,
    metric_type     VARCHAR(50) NOT NULL,
    metric_name     VARCHAR(200) NOT NULL,
    model_name      VARCHAR(50),
    current_value   FLOAT NOT NULL DEFAULT 0.0,
    previous_value  FLOAT NOT NULL DEFAULT 0.0,
    change_pct      FLOAT,
    trend           VARCHAR(10),
    metric_metadata JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_weekly_review_metrics_review ON weekly_review_metrics(weekly_review_id);

CREATE TABLE geo_rules (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID REFERENCES customers(id) ON DELETE CASCADE,
    model_name      VARCHAR(50) NOT NULL,
    rule_name       VARCHAR(300) NOT NULL,
    rule_category   VARCHAR(50) NOT NULL,
    rule_content    TEXT NOT NULL,
    confidence      FLOAT NOT NULL DEFAULT 0.0,
    evidence        JSONB NOT NULL DEFAULT '[]',
    version         INTEGER NOT NULL DEFAULT 1,
    is_latest       BOOLEAN NOT NULL DEFAULT true,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    discovered_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_geo_rules_model ON geo_rules(model_name, is_latest);
CREATE INDEX idx_geo_rules_customer ON geo_rules(customer_id, model_name);

-- ══════════════════════════════════════════════════════════════════
-- P1 Seed Data: Default GEO Rules for Major Models
-- ══════════════════════════════════════════════════════════════════

INSERT INTO geo_rules (model_name, rule_name, rule_category, rule_content, confidence, version, is_latest) VALUES
-- 豆包 (字节)
('doubao', '豆包-头条生态权重', 'source_weight', '今日头条、抖音图文专栏内容在豆包搜索中享有更高权重，建议企业重点布局头条号内容', 0.85, 1, true),
('doubao', '豆包-内容深度偏好', 'content_quality', '豆包偏好结构化、有数据支撑的深度内容，AI摘要类回答更易获得推荐', 0.78, 1, true),
('doubao', '豆包-时效性要求', 'freshness', '豆包对3个月内更新内容的权重显著高于旧内容，建议保持知识库高频更新', 0.72, 1, true),
-- 文心一言 (百度)
('wenxin', '文心-百度生态权重', 'source_weight', '百家号、百度百科、百度知道内容在文心一言中占据主导信源地位', 0.90, 1, true),
('wenxin', '文心-结构化数据偏好', 'content_quality', '文心一言偏好企业官网结构化数据、产品参数表格式内容', 0.76, 1, true),
('wenxin', '文心-权威信源加分', 'source_weight', '百度百科词条收录是文心一言推荐的强加分项，未收录企业曝光概率大幅降低', 0.88, 1, true),
-- 通义千问 (阿里)
('qianwen', '千问-阿里生态权重', 'source_weight', '阿里云社区、1688专栏、钉钉文档内容在千问中享有生态优势', 0.82, 1, true),
('qianwen', '千问-商业可信度', 'content_quality', '千问对企业资质证书、合作伙伴案例的引用比例较高，建议强化商业背书内容', 0.74, 1, true),
-- 腾讯元宝
('yuanbao', '元宝-微信生态权重', 'source_weight', '微信公众号、视频号内容在元宝中权重显著，企业公众号运营是必选项', 0.87, 1, true),
('yuanbao', '元宝-用户评价权重', 'recommendation', '元宝对第三方用户评价、口碑数据的引用较多，正负面评价均影响推荐', 0.70, 1, true),
-- 讯飞星火
('xinghuo', '星火-政企权威偏好', 'source_weight', '星火对政府网站、行业期刊、学术论文等权威信源给予最高权重', 0.84, 1, true),
('xinghuo', '星火-专业术语加分', 'content_quality', '星火偏好使用行业标准术语的专业内容，建议避免过度口语化表达', 0.71, 1, true),
-- DeepSeek
('deepseek', 'DeepSeek-技术深度偏好', 'content_quality', 'DeepSeek对技术白皮书、深度技术文章有极高评分，技术型内容易获得推荐', 0.80, 1, true),
('deepseek', 'DeepSeek-开源社区信源', 'source_weight', 'DeepSeek对GitHub、技术社区等开源平台内容引用频繁，开发者社区存在感重要', 0.73, 1, true),
-- Kimi
('kimi', 'Kimi-长文本偏好', 'content_quality', 'Kimi擅长处理长文本，详尽的产品说明、行业分析报告更易被发现和引用', 0.77, 1, true),
('kimi', 'Kimi-跨平台信源', 'source_weight', 'Kimi对多源交叉验证的信息给予更高信任，建议多平台布局信源矩阵', 0.69, 1, true);

-- P1 Default Permissions
INSERT INTO permissions (code, resource, action, description) VALUES
('detection:read',   'detection', 'read',   'View detection tasks and results'),
('detection:create', 'detection', 'create', 'Create and run detection tasks'),
('detection:update', 'detection', 'update', 'Update detection task config'),
('diagnosis:read',   'diagnosis', 'read',   'View diagnosis reports'),
('diagnosis:create', 'diagnosis', 'create', 'Generate diagnosis reports'),
('review:read',      'review',    'read',   'View weekly review reports'),
('review:create',    'review',    'create', 'Generate weekly reviews'),
('rule:read',        'rule',      'read',   'View GEO rules'),
('rule:update',      'rule',      'update', 'Update GEO rules')
ON CONFLICT (code) DO NOTHING;

-- Grant new P1 permissions to existing roles
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.code = 'super_admin' AND r.customer_id IS NULL
  AND p.resource IN ('detection', 'diagnosis', 'rule')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.code = 'admin' AND r.customer_id IS NULL
  AND p.resource IN ('detection', 'diagnosis', 'rule') AND p.action != 'update'
ON CONFLICT (role_id, permission_id) DO NOTHING;
