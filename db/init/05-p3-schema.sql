-- ============================================================================
-- GEO AI Platform — P3 Schema Additions
-- Billing, Industry Templates, White-Label, BI Dashboards
-- ============================================================================

-- ══════════════════════════════════════════════════════════════════
-- P3: SaaS Billing System (5 tables)
-- ══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS plans (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(200) NOT NULL,
    code            VARCHAR(50) NOT NULL UNIQUE,
    description     TEXT,
    tier            INTEGER NOT NULL DEFAULT 1,
    monthly_price   NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    yearly_price    NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    features        JSONB NOT NULL DEFAULT '[]',
    quotas          JSONB NOT NULL DEFAULT '{}',
    is_active       BOOLEAN NOT NULL DEFAULT true,
    is_public       BOOLEAN NOT NULL DEFAULT true,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orders (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    plan_id         UUID NOT NULL REFERENCES plans(id) ON DELETE RESTRICT,
    order_type      VARCHAR(30) NOT NULL,
    billing_cycle   VARCHAR(10) NOT NULL DEFAULT 'monthly',
    amount          NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    status          VARCHAR(30) NOT NULL DEFAULT 'pending',
    start_date      DATE NOT NULL,
    end_date        DATE,
    payment_method  VARCHAR(50),
    payment_ref     VARCHAR(200),
    notes           TEXT,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id, status);

CREATE TABLE IF NOT EXISTS payments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    order_id        UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    amount          NUMERIC(10, 2) NOT NULL,
    payment_method  VARCHAR(50) NOT NULL,
    transaction_id  VARCHAR(200),
    status          VARCHAR(30) NOT NULL DEFAULT 'pending',
    paid_at         TIMESTAMPTZ,
    raw_response    JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS usage_records (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    usage_type      VARCHAR(50) NOT NULL,
    usage_count     INTEGER NOT NULL DEFAULT 0,
    quota_limit     INTEGER NOT NULL DEFAULT 0,
    usage_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_usage_customer_date ON usage_records(customer_id, usage_type, usage_date);

CREATE TABLE IF NOT EXISTS quota_alerts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    usage_type      VARCHAR(50) NOT NULL,
    threshold_pct   INTEGER NOT NULL DEFAULT 80,
    is_triggered    BOOLEAN NOT NULL DEFAULT false,
    triggered_at    TIMESTAMPTZ,
    acknowledged    BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ══════════════════════════════════════════════════════════════════
-- P3: Industry Templates (1 table)
-- ══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS industry_templates (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(200) NOT NULL,
    code            VARCHAR(50) NOT NULL UNIQUE,
    industry        VARCHAR(100) NOT NULL,
    description     TEXT,
    icon            VARCHAR(100),
    preset_keywords JSONB NOT NULL DEFAULT '[]',
    pain_points     JSONB NOT NULL DEFAULT '[]',
    asset_structure JSONB NOT NULL DEFAULT '[]',
    recommended_channels JSONB NOT NULL DEFAULT '[]',
    content_strategy JSONB NOT NULL DEFAULT '{}',
    competitor_suggestions JSONB NOT NULL DEFAULT '[]',
    use_case        TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    is_system       BOOLEAN NOT NULL DEFAULT true,
    customer_id     UUID REFERENCES customers(id) ON DELETE CASCADE,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ══════════════════════════════════════════════════════════════════
-- P3: White-Label Branding (extend existing customer_settings)
-- ══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS tenant_branding (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE UNIQUE,
    brand_name      VARCHAR(200),
    logo_url        VARCHAR(1000),
    favicon_url     VARCHAR(1000),
    primary_color   VARCHAR(7) DEFAULT '#409eff',
    secondary_color VARCHAR(7) DEFAULT '#67c23a',
    custom_domain   VARCHAR(500),
    login_bg_url    VARCHAR(1000),
    footer_text     VARCHAR(500),
    is_enabled      BOOLEAN NOT NULL DEFAULT false,
    updated_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ══════════════════════════════════════════════════════════════════
-- P3: Seed Data — Plans
-- ══════════════════════════════════════════════════════════════════

INSERT INTO plans (name, code, tier, monthly_price, yearly_price, features, quotas, description) VALUES
('基础版', 'basic', 1, 999.00, 9990.00,
 '["3个用户","500条知识库资产","50篇内容/月","5个探测任务","基础报表"]',
 '{"max_users":3,"max_kb_assets":500,"max_content_month":50,"max_detection_tasks":5,"max_llm_calls_month":500,"max_channels":5}',
 '适合小微企业，基础GEO能力'),
('专业版', 'professional', 2, 2999.00, 29990.00,
 '["10个用户","2000条知识库资产","200篇内容/月","20个探测任务","高级报表","向量知识库","自动发布3渠道"]',
 '{"max_users":10,"max_kb_assets":2000,"max_content_month":200,"max_detection_tasks":20,"max_llm_calls_month":2000,"max_channels":10}',
 '适合成长型企业，全功能GEO运营'),
('企业版', 'enterprise', 3, 8999.00, 89990.00,
 '["无限用户","10000条知识库资产","1000篇内容/月","100个探测任务","全功能报表","向量知识库","全渠道自动发布","白标品牌","私有化部署","专属客服"]',
 '{"max_users":999,"max_kb_assets":10000,"max_content_month":1000,"max_detection_tasks":100,"max_llm_calls_month":10000,"max_channels":50}',
 '适合大型企业及代理商，无限GEO能力')
ON CONFLICT (code) DO NOTHING;

-- ══════════════════════════════════════════════════════════════════
-- P3: Seed Data — Industry Templates (5 industries)
-- ══════════════════════════════════════════════════════════════════

INSERT INTO industry_templates (name, code, industry, description, icon, preset_keywords, pain_points, asset_structure, recommended_channels, content_strategy, competitor_suggestions, use_case) VALUES
('制造业解决方案', 'manufacturing', 'manufacturing', '面向制造业企业的GEO全案模板，覆盖产品型号、资质认证、行业案例', 'Setting',
 '[{"word":"工业设备供应商","type":"broad"},{"word":"自动化生产线","type":"product"},{"word":"智能制造解决方案","type":"scenario"},{"word":"设备选型对比","type":"comparison"}]',
 '["产品参数不详","资质认证缺失","行业案例不足","技术白皮书缺乏"]',
 '[{"name":"企业简介","asset_type":"basic","category":"基础资产","description":"公司简介、成立时间、主营产品"},{"name":"产品参数表","asset_type":"basic","category":"基础资产","description":"各型号产品详细参数"},{"name":"资质证书","asset_type":"basic","category":"基础资产","description":"ISO、CE等认证"},{"name":"客户案例","asset_type":"marketing","category":"营销资产","description":"成功合作案例详情"},{"name":"技术白皮书","asset_type":"multimodal","category":"多模态资产","description":"技术方案文档"}]',
 '[{"name":"百度百科","channel_type":"encyclopedia","tier":1},{"name":"百家号","channel_type":"baijiahao","tier":2},{"name":"行业期刊","channel_type":"press","tier":3}]',
 '{"tone_style":"专业严谨","content_types":["产品介绍","技术方案","案例分享"],"seo_tips":"重点覆盖长尾产品型号词"}',
 '[{"name":"同行A"},{"name":"同行B"}]',
 '适用于机械设备、自动化、精密制造等制造型企业'),

('本地服务解决方案', 'local_service', 'local_service', '面向本地生活服务类企业的GEO模板，侧重本地搜索曝光和口碑管理', 'Service',
 '[{"word":"本地服务推荐","type":"broad"},{"word":"附近XX服务","type":"product"},{"word":"本地服务哪家好","type":"comparison"}]',
 '["本地搜索排名低","用户评价少","服务内容展示不清晰","线上预约信息缺失"]',
 '[{"name":"服务介绍","asset_type":"basic","category":"基础资产","description":"服务项目、价格、流程"},{"name":"门店信息","asset_type":"basic","category":"基础资产","description":"地址、营业时间、联系方式"},{"name":"用户评价","asset_type":"marketing","category":"营销资产","description":"精选好评、案例展示"}]',
 '[{"name":"企业官网","channel_type":"cms","tier":1},{"name":"微信公众号","channel_type":"wechat_mp","tier":2},{"name":"本地论坛","channel_type":"forum","tier":3}]',
 '{"tone_style":"温暖亲和","content_types":["服务介绍","客户故事","优惠活动"],"seo_tips":"覆盖地名+服务名组合词"}',
 '[{"name":"本地竞品A"},{"name":"本地竞品B"}]',
 '适用于家政、装修、摄影、培训、餐饮等本地服务类企业'),

('电商品牌解决方案', 'ecommerce', 'ecommerce', '面向电商品牌的全渠道GEO模板，侧重产品种草和品牌搜索', 'Goods',
 '[{"word":"XX品牌怎么样","type":"broad"},{"word":"XX产品测评","type":"product"},{"word":"同价位推荐","type":"comparison"},{"word":"XX使用场景","type":"scenario"}]',
 '["品牌词搜索量低","产品种草内容少","竞品对比信源不足","用户口碑分散"]',
 '[{"name":"品牌故事","asset_type":"basic","category":"基础资产","description":"品牌理念、创始人故事"},{"name":"产品线","asset_type":"basic","category":"基础资产","description":"各系列产品详情"},{"name":"种草测评","asset_type":"marketing","category":"营销资产","description":"KOL合作测评内容"},{"name":"产品图集","asset_type":"multimodal","category":"多模态资产","description":"高清产品图、场景图"}]',
 '[{"name":"今日头条","channel_type":"toutiao","tier":2},{"name":"小红书","channel_type":"social","tier":2},{"name":"知乎","channel_type":"forum","tier":3}]',
 '{"tone_style":"生动活泼","content_types":["产品种草","对比测评","使用教程"],"seo_tips":"重点覆盖品类词+品牌词组合"}',
 '[{"name":"竞品品牌A"},{"name":"竞品品牌B"},{"name":"竞品品牌C"}]',
 '适用于消费品牌、DTC品牌、电商卖家等'),

('教育培训解决方案', 'education', 'education', '面向教育机构的GEO模板，侧重课程搜索和口碑传播', 'Reading',
 '[{"word":"XX培训哪家好","type":"broad"},{"word":"XX课程价格","type":"product"},{"word":"在线教育推荐","type":"comparison"},{"word":"考证培训方案","type":"scenario"}]',
 '["课程信息展示不全","师资介绍缺失","学员评价不足","试听体验内容少"]',
 '[{"name":"机构简介","asset_type":"basic","category":"基础资产","description":"机构资质、办学历史"},{"name":"课程体系","asset_type":"basic","category":"基础资产","description":"各课程详情、价格、班型"},{"name":"师资力量","asset_type":"basic","category":"基础资产","description":"教师资质、经验"},{"name":"学员案例","asset_type":"marketing","category":"营销资产","description":"成功学员故事"},{"name":"试听视频","asset_type":"multimodal","category":"多模态资产","description":"课程试听片段"}]',
 '[{"name":"百度百科","channel_type":"encyclopedia","tier":1},{"name":"知乎","channel_type":"forum","tier":2},{"name":"教育垂直媒体","channel_type":"press","tier":3}]',
 '{"tone_style":"专业可信","content_types":["课程介绍","师资展示","学员故事","行业解读"],"seo_tips":"覆盖课程名+城市+价格等组合词"}',
 '[{"name":"竞品机构A"},{"name":"竞品机构B"}]',
 '适用于K12、职业技能、语言培训、兴趣教育等'),

('医疗健康解决方案', 'healthcare', 'healthcare', '面向医疗健康机构的GEO模板，侧重权威信源和合规内容', 'FirstAidKit',
 '[{"word":"XX科室推荐","type":"broad"},{"word":"XX疾病治疗","type":"product"},{"word":"治疗方案对比","type":"comparison"},{"word":"就医指南","type":"scenario"}]',
 '["医疗资质展示不足","医生团队介绍缺失","科普内容匮乏","预约渠道分散"]',
 '[{"name":"医院简介","asset_type":"basic","category":"基础资产","description":"等级、科室、特色"},{"name":"医生团队","asset_type":"basic","category":"基础资产","description":"专家履历、擅长领域"},{"name":"特色科室","asset_type":"basic","category":"基础资产","description":"科室详情、设备"},{"name":"健康科普","asset_type":"marketing","category":"营销资产","description":"疾病预防、保健知识"},{"name":"就医指南","asset_type":"multimodal","category":"多模态资产","description":"就诊流程视频"}]',
 '[{"name":"百度百科","channel_type":"encyclopedia","tier":1},{"name":"政府卫生平台","channel_type":"gov","tier":1},{"name":"医疗行业期刊","channel_type":"press","tier":3}]',
 '{"tone_style":"严谨权威","content_types":["健康科普","医生访谈","科室介绍"],"seo_tips":"严格遵循医疗广告法规，以科普内容为主"}',
 '[{"name":"同城医院A"},{"name":"同城医院B"}]',
 '适用于医院、诊所、体检中心、健康管理平台等')
ON CONFLICT (code) DO NOTHING;

-- P3 New Permissions
INSERT INTO permissions (code, resource, action, description) VALUES
('billing:read',     'billing',  'read',   'View plans and orders'),
('billing:create',   'billing',  'create', 'Create orders'),
('billing:manage',   'billing',  'manage', 'Manage plans and payments'),
('template:read',    'template', 'read',   'View industry templates'),
('template:manage',  'template', 'manage', 'Manage industry templates')
ON CONFLICT (code) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.code = 'super_admin' AND r.customer_id IS NULL AND p.resource IN ('billing', 'template')
ON CONFLICT (role_id, permission_id) DO NOTHING;
