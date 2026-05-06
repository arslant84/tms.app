export interface Permission {
  id: string;
  name: string;
  codename: string;
  description?: string;
}

export interface Role {
  id: string;
  name: string;
  description?: string;
  permissions?: Permission[];
}

export interface Department {
  id: string;
  name: string;
  code?: string;
  description?: string;
  is_active: boolean;
  user_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface DepartmentListItem {
  id: string;
  name: string;
  code?: string;
  is_active: boolean;
}

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role | string; // Can be Role object or role name string from backend
  department: Department | DepartmentListItem | string | null; // Can be Department object, list item, or ID string
  is_admin: boolean;
  is_active: boolean;
  // Permissions array for RBAC
  permissions?: string[];
  // Staff identifiers
  staff_id?: string;
  staff_no?: string;
  // These fields are computed from name when needed
  firstName?: string;
  lastName?: string;
  // Profile image URL (or base64 data)
  avatar?: string;
  profile_photo?: string;
  // Gender
  gender?: string;
  // Phone number
  phone?: string;
  // Position/Job title
  position?: string;
  // Last login timestamp
  last_login_at?: string;
  // SECURITY: Password change required flag
  password_change_required?: boolean;
  // MFA flags
  mfa_enabled?: boolean;
  mfa_setup_required?: boolean;
}

export interface AuthMeta {
  token?: string;
  refresh_token?: string;
  expires_in?: number;
  token_type?: string;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  data: Partial<User> & {
    mfa_required?: boolean;
    challenge_token?: string;
  };
  meta?: AuthMeta;
}

export interface LoginResult {
  type: 'success' | 'mfa_required' | 'mfa_setup_required';
  user?: User;
}
