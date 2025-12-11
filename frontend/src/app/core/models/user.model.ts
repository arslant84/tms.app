export interface Role {
  id: string;
  name: string;
  description?: string;
  permissions?: any[];
}

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role | UserRole | any; // Can be Role object or simple string
  department: string;
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
  // Last login timestamp
  last_login_at?: string;
}

export enum UserRole {
  EMPLOYEE = 'employee',
  FOCAL = 'focal',
  HOD = 'hod',
  TICKETING_CLERK = 'ticketing_clerk',
  EXTERNAL = 'external',
  ADMIN = 'admin'
}

export interface AuthResponse {
  token: string;
  user: Partial<User>;
}
