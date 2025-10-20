export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
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
  // Profile image URL
  avatar?: string;
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
  user: {
    id: number;
    username?: string;
    name?: string;
    email: string;
    role: UserRole;
    department?: string;
    is_admin?: boolean;
  };
}
