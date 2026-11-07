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

export type ProjectStatus = 'CURRENT' | 'PAST';

export interface ProjectPublic {
  id: string;
  owner_id: string;
  company_id: string;
  title: string;
  description: string;
  style: string;
  category: string;
  budget_min: number;
  budget_max: number;
  status: ProjectStatus;
  images: string[];
  tags: string[];
  view_count: number;
  shortlist_count: number;
  created_at: string;
  updated_at: string;
}

export interface SearchResponse {
  items: ProjectPublic[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface SearchParams {
  keyword?: string;
  category?: string;
  style?: string;
  budget_min?: number;
  budget_max?: number;
  page?: number;
  page_size?: number;
}

export interface BudgetRange {
  min: number;
  max: number;
  step: number;
}

export interface Catalogue {
  categories: string[];
  styles: string[];
  budget: BudgetRange;
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

export interface ProjectInput {
  title: string;
  description: string;
  category: string;
  style: string;
  budget_min: number;
  budget_max: number;
  images: string[];
  tags: string[];
}

export interface TagSuggestion {
  palette: { hex: string; percent: number }[];
  tags: string[];
  width: number;
  height: number;
}

export interface ShortlistResponse {
  project_ids: string[];
  items: ProjectPublic[];
}

export type QuoteRequestState =
  | 'PENDING'
  | 'ANSWERED'
  | 'ACCEPTED'
  | 'DECLINED'
  | 'CANCELLED'
  | 'REFUSED'
  | 'EXPIRED';

export type QuoteState =
  | 'OFFERED'
  | 'ACCEPTED'
  | 'DECLINED'
  | 'SUPERSEDED'
  | 'EXPIRED';

export interface QuoteCounter {
  id: string;
  target_cents: number;
  note: string;
  created_at: string;
}

export interface QuotePublic {
  id: string;
  request_id: string;
  version: number;
  total_cents: number;
  gst_included: boolean;
  gst_rate_bp: number;
  gst_cents: number;
  grand_total_cents: number;
  valid_until: string;
  note: string;
  state: QuoteState;
  created_at: string;
}

export interface QuoteRequestPublic {
  id: string;
  customer_id: string;
  company_id: string;
  project_id: string | null;
  title: string;
  scope: string;
  budget_min_cents: number;
  budget_max_cents: number;
  target_cents: number | null;
  state: QuoteRequestState;
  counters: QuoteCounter[];
  closed_reason: string;
  created_at: string;
  updated_at: string;
}

export interface QuoteRequestDetail extends QuoteRequestPublic {
  quotes: QuotePublic[];
}