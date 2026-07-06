export interface UserInfo {
  id: string
  email: string
  display_name: string
  phone?: string
  avatar_url?: string
  is_super_admin: boolean
  is_active: boolean
  customer_id?: string
  last_login_at?: string
  created_at: string
  roles?: RoleBrief[]
}

export interface RoleBrief {
  id: string
  name: string
  code: string
  permissions?: PermissionBrief[]
}

export interface RoleInfo {
  id: string
  name: string
  code: string
  description?: string
  is_system: boolean
  created_at: string
  permissions: PermissionBrief[]
}

export interface PermissionBrief {
  id: string
  code: string
  resource: string
  action: string
}

export interface PermissionInfo {
  id: string
  code: string
  resource: string
  action: string
  description?: string
}
