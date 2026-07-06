-- P5: Sub-accounts, Payment Records, Demo Query, Role-based Access
ALTER TABLE users ADD COLUMN IF NOT EXISTS role_type VARCHAR(30) NOT NULL DEFAULT 'admin';

CREATE TABLE IF NOT EXISTS sub_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    email VARCHAR(320) NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    company_name VARCHAR(300),
    is_active BOOLEAN NOT NULL DEFAULT true,
    service_start DATE NOT NULL,
    service_end DATE,
    created_by UUID REFERENCES users(id),
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(email)
);

CREATE TABLE IF NOT EXISTS payment_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    sub_account_id UUID REFERENCES sub_accounts(id) ON DELETE SET NULL,
    company_name VARCHAR(300) NOT NULL,
    plan_name VARCHAR(100) NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    billing_cycle VARCHAR(10) NOT NULL DEFAULT 'yearly',
    service_start DATE NOT NULL,
    service_end DATE NOT NULL,
    payment_method VARCHAR(50),
    payment_ref VARCHAR(200),
    notes TEXT,
    recorded_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO permissions (code, resource, action, description) VALUES
('subaccount:read', 'subaccount', 'read', 'View sub-accounts'),
('subaccount:create', 'subaccount', 'create', 'Create sub-accounts'),
('subaccount:manage', 'subaccount', 'manage', 'Manage sub-accounts (reset/disable)'),
('payment:read', 'payment', 'read', 'View payment records'),
('payment:create', 'payment', 'create', 'Create payment records')
ON CONFLICT (code) DO NOTHING;
