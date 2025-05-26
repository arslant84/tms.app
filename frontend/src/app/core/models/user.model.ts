export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  department: string;
  is_admin: boolean;
  is_active: boolean;
  // These fields are computed from name when needed
  firstName?: string;
  lastName?: string;
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
  access_token: string;
  token_type: string;
  user_id: number;
  name: string;
  role: UserRole;
  is_admin: boolean;
}
