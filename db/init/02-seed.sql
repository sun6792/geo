-- ============================================================================
-- GEO AI Platform — Seed Data
-- Creates: platform super admin, default roles, all permissions
-- ============================================================================

-- ── Default Permissions (24 standard permissions) ───────────────────────────

INSERT INTO permissions (code, resource, action, description) VALUES
-- Customer management
('customer:read',   'customer', 'read',   'View customer details'),
('customer:create', 'customer', 'create', 'Create new customers'),
('customer:update', 'customer', 'update', 'Update customer settings'),
('customer:delete', 'customer', 'delete', 'Delete/suspend customers'),

-- Account management
('account:read',    'account',  'read',   'View users and roles'),
('account:create',  'account',  'create', 'Create users and roles'),
('account:update',  'account',  'update', 'Update users and assign roles'),
('account:delete',  'account',  'delete', 'Deactivate users'),

-- Knowledge base
('kb:read',         'kb',       'read',   'View knowledge base assets'),
('kb:create',       'kb',       'create', 'Create and upload assets'),
('kb:update',       'kb',       'update', 'Edit assets and categories'),
('kb:delete',       'kb',       'delete', 'Archive assets'),

-- Content creation
('content:read',    'content',  'read',   'View content briefs and drafts'),
('content:create',  'content',  'create', 'Create briefs and generate content'),
('content:update',  'content',  'update', 'Edit drafts manually'),
('content:delete',  'content',  'delete', 'Archive content'),

-- Review workflow
('review:read',     'review',   'read',   'View review records'),
('review:approve',  'review',   'approve','Approve or reject content'),
('review:comment',  'review',   'comment','Add review comments'),

-- Publishing
('publish:read',    'publish',  'read',   'View publish schedules and records'),
('publish:create',  'publish',  'create', 'Schedule and execute publishing'),
('publish:update',  'publish',  'update', 'Update publish configurations'),

-- System
('system:read',     'system',   'read',   'View operation logs and health'),
('system:manage',   'system',   'manage', 'Manage system configuration')
ON CONFLICT (code) DO NOTHING;

-- ── Default Roles ───────────────────────────────────────────────────────────

-- Platform Super Admin (customer_id = NULL, system-wide)
INSERT INTO roles (customer_id, name, code, description, is_system) VALUES
(NULL, '超级管理员', 'super_admin', 'Platform super administrator with all permissions', true)
ON CONFLICT (customer_id, code) DO NOTHING;

-- Tenant-scoped roles (customer_id = NULL means global role template)
INSERT INTO roles (customer_id, name, code, description, is_system) VALUES
(NULL, '管理员', 'admin', 'Tenant administrator', true),
(NULL, '编辑员', 'editor', 'Content editor with KB and content creation access', true),
(NULL, '审核员', 'reviewer', 'Content reviewer with approval authority', true),
(NULL, '观察员', 'viewer', 'Read-only access to all modules', true)
ON CONFLICT (customer_id, code) DO NOTHING;

-- ── Role-Permission Assignments ─────────────────────────────────────────────
-- Assign all permissions to super_admin
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.code = 'super_admin' AND r.customer_id IS NULL
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Assign permissions to admin (all except customer management for tenant admin)
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.code = 'admin' AND r.customer_id IS NULL
  AND p.code NOT IN ('customer:create', 'customer:delete', 'system:manage')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Assign permissions to editor
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.code = 'editor' AND r.customer_id IS NULL
  AND p.code IN (
    'kb:read', 'kb:create', 'kb:update',
    'content:read', 'content:create', 'content:update',
    'publish:read', 'review:read', 'system:read'
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Assign permissions to reviewer
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.code = 'reviewer' AND r.customer_id IS NULL
  AND p.code IN (
    'kb:read', 'content:read', 'review:read', 'review:approve', 'review:comment',
    'publish:read', 'system:read'
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Assign permissions to viewer
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.code = 'viewer' AND r.customer_id IS NULL
  AND p.action = 'read'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- ── Platform Super Admin User ───────────────────────────────────────────────
-- Create a default platform customer for the super admin
INSERT INTO customers (id, name, slug, owner_email, company_name, subscription_tier, max_users, max_kb_assets)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'GEO AI Platform',
    'geoai-platform',
    'admin@geoai.com',
    'GEO AI Tech',
    'enterprise',
    999,
    9999
) ON CONFLICT (slug) DO NOTHING;

-- Create super admin user (password: admin123 — CHANGE IN PRODUCTION!)
-- bcrypt hash for 'admin123'
INSERT INTO users (id, customer_id, email, password_hash, display_name, is_super_admin, is_active)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001',
    'admin@geoai.com',
    '$2b$12$nTUJunHt.2isxoGyI.x2/uwcKD4pwSTORFh7LigeaKssSWPAFIEEK',
    'Platform Admin',
    true,
    true
) ON CONFLICT (customer_id, email) DO NOTHING;

-- Assign super_admin role to platform admin
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u, roles r
WHERE u.email = 'admin@geoai.com' AND r.code = 'super_admin'
ON CONFLICT (user_id, role_id) DO NOTHING;

-- ── Demo Customer (for testing) ─────────────────────────────────────────────
INSERT INTO customers (id, name, slug, owner_email, company_name, industry, subscription_tier)
VALUES (
    '00000000-0000-0000-0000-000000000002',
    'Demo Enterprise',
    'demo-enterprise',
    'demo@example.com',
    'Demo Corp Ltd.',
    'Technology',
    'professional'
) ON CONFLICT (slug) DO NOTHING;

-- Create demo admin user (password: demo123)
INSERT INTO users (id, customer_id, email, password_hash, display_name, is_active)
VALUES (
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000002',
    'demo@example.com',
    '$2b$12$nTUJunHt.2isxoGyI.x2/uwcKD4pwSTORFh7LigeaKssSWPAFIEEK',
    'Demo Admin',
    true
) ON CONFLICT (customer_id, email) DO NOTHING;

-- Assign admin role to demo user
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u, roles r
WHERE u.email = 'demo@example.com' AND r.code = 'admin'
ON CONFLICT (user_id, role_id) DO NOTHING;

-- ── Default System Configuration ────────────────────────────────────────────
INSERT INTO system_config (config_key, config_value, description) VALUES
('review.checklist.internal', '[
    {"text": "事实准确性：所有数据、参数从知识库读取，无虚构信息", "order": 1},
    {"text": "合规性：内容不违反广告法、无绝对化用语", "order": 2},
    {"text": "信息一致性：与知识库中企业信息、产品参数完全一致", "order": 3},
    {"text": "内容质量：逻辑清晰、结构完整、无语法错误", "order": 4},
    {"text": "SEO友好：标题含核心关键词、正文自然分布长尾词", "order": 5}
]', 'Default internal review checklist'),
('review.checklist.client', '[
    {"text": "品牌调性：内容是否符合企业品牌形象和调性", "order": 1},
    {"text": "信息准确：企业信息、联系方式、资质表述是否准确", "order": 2},
    {"text": "商业诉求：内容是否准确传达了产品/服务的核心卖点", "order": 3}
]', 'Default client review checklist')
ON CONFLICT (config_key) DO NOTHING;
