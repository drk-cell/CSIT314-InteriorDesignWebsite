export type Role = 'CUSTOMER' | 'DESIGNER' | 'ADMIN' | 'PLATFORM_MANAGER';

export type Status = 'PENDING' | 'ACTIVE' | 'SUSPENDED';

/** Roles a visitor may choose when creating an account. */
export type RegistrationRole = Extract<Role, 'CUSTOMER' | 'DESIGNER'>;

export interface AccountPublic {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  status: Status;
  created_at: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  time: string;
}

export interface CompanyPublic {
  id: string;
  owner_id: string;
  name: string;
  description: string;
  contact_email: string;
  contact_phone: string;
  location: string;
  logo_url: string;
  created_at: string;
  updated_at: string;
}

export interface CompanyInput {
  name: string;
  description: string;
  contact_email: string;
  contact_phone: string;
  location: string;
  logo_url: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  display_name: string;
  role: RegistrationRole;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  account: AccountPublic;
}