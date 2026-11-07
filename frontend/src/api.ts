import type {
  AccountPublic,
  Catalogue,
  CategoryPublic,
  CompanyInput,
  CompanyPublic,
  HealthResponse,
  LoginRequest,
  RegisterRequest,
  Report,
  SearchParams,
  SearchResponse,
  ProjectInput,
  ProjectPublic,
  ProjectStatus,
  QuotePublic,
  QuoteRequestDetail,
  QuoteRequestPublic,
  QuoteRequestState,
  ShortlistResponse,
  Status,
  TagSuggestion,
  TokenResponse,
} from './types';

const API_BASE = '/api';
const TOKEN_KEY = 'idp.token';

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

function readDetail(body: unknown, fallback: string): string {
  if (body === null || typeof body !== 'object' || !('detail' in body)) {
    return fallback;
  }
  const detail = (body as { detail: unknown }).detail;
  if (typeof detail === 'string' && detail.trim() !== '') {
    return detail;
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((entry) => {
        if (entry === null || typeof entry !== 'object' || !('msg' in entry)) return null;
        const message = (entry as { msg: unknown }).msg;
        return typeof message === 'string' ? message : null;
      })
      .filter((message): message is string => message !== null);
    if (messages.length > 0) return messages.join('; ');
  }
  return fallback;
}

async function readBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (text === '') return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Accept', 'application/json');
  if (init.body !== undefined) {
    headers.set('Content-Type', 'application/json');
  }
  const token = getToken();
  if (token !== null) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, 'Cannot reach the server. Check that the backend is running.');
  }

  const body = await readBody(response);
  if (!response.ok) {
    throw new ApiError(
      response.status,
      readDetail(body, `Request failed with status ${response.status}.`),
    );
  }
  return body as T;
}

export function health(): Promise<HealthResponse> {
  return request<HealthResponse>('/health');
}

export function register(body: RegisterRequest): Promise<AccountPublic> {
  return request<AccountPublic>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function login(body: LoginRequest): Promise<TokenResponse> {
  return request<TokenResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function me(): Promise<AccountPublic> {
  return request<AccountPublic>('/auth/me');
}

export function adminListAccounts(status?: Status): Promise<AccountPublic[]> {
  const query = status === undefined ? '' : `?status=${status}`;
  return request<AccountPublic[]>(`/admin/accounts${query}`);
}

export function adminApprove(accountId: string): Promise<AccountPublic> {
  return request<AccountPublic>(`/admin/accounts/${accountId}/approve`, { method: 'POST' });
}

export function adminSuspend(accountId: string): Promise<AccountPublic> {
  return request<AccountPublic>(`/admin/accounts/${accountId}/suspend`, { method: 'POST' });
}

export function myCompany(): Promise<CompanyPublic> {
  return request<CompanyPublic>('/companies/me');
}

export function createCompany(body: CompanyInput): Promise<CompanyPublic> {
  return request<CompanyPublic>('/companies', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function updateMyCompany(body: CompanyInput): Promise<CompanyPublic> {
  return request<CompanyPublic>('/companies/me', {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
}

export function companyById(companyId: string): Promise<CompanyPublic> {
  return request<CompanyPublic>(`/companies/${companyId}`);
}

export function listCompanies(): Promise<CompanyPublic[]> {
  return request<CompanyPublic[]>('/companies');
}

export function searchProjects(params: SearchParams): Promise<SearchResponse> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') {
      query.set(key, String(value));
    }
  }
  return request<SearchResponse>(`/projects/search?${query.toString()}`);
}

export function getCatalogue(): Promise<Catalogue> {
  return request<Catalogue>('/catalogue');
}

export function createProject(
  body: ProjectInput
): Promise<ProjectPublic> {
  return request<ProjectPublic>('/projects', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function getProject(
  projectId: string
): Promise<ProjectPublic> {
  return request<ProjectPublic>(
    `/projects/${encodeURIComponent(projectId)}`
  );
}

export function updateProject(
  projectId: string,
  body: Partial<ProjectInput> & { status?: ProjectStatus }
): Promise<ProjectPublic> {
  return request<ProjectPublic>(
    `/projects/${encodeURIComponent(projectId)}`,
    {
      method: 'PATCH',
      body: JSON.stringify(body),
    }
  );
}

export function myProjects(
  filters: {
    status?: ProjectStatus;
    name?: string;
  } = {}
): Promise<ProjectPublic[]> {
  const query = new URLSearchParams();

  if (filters.status) {
    query.set('status', filters.status);
  }

  if (filters.name?.trim()) {
    query.set('name', filters.name.trim());
  }

  const search = query.toString();
  const path = search
    ? `/projects/mine?${search}`
    : '/projects/mine';

  return request<ProjectPublic[]>(path);
}
export function suggestTags(
  projectId: string,
  imageIndex = 0
): Promise<TagSuggestion> {
  return request<TagSuggestion>(
    `/projects/${encodeURIComponent(projectId)}/suggest-tags?image_index=${imageIndex}`,
    { method: 'POST' }
  );
}

export function recordView(projectId: string): Promise<void> {
  return request<void>(`/projects/${encodeURIComponent(projectId)}/view`, {
    method: 'POST',
  });
}

export function getShortlist(): Promise<ShortlistResponse> {
  return request<ShortlistResponse>('/shortlist');
}

export function saveProject(projectId: string): Promise<ShortlistResponse> {
  return request<ShortlistResponse>(
    `/shortlist/${encodeURIComponent(projectId)}`,
    { method: 'POST' }
  );
}

export function unsaveProject(projectId: string): Promise<void> {
  return request<void>(`/shortlist/${encodeURIComponent(projectId)}`, {
    method: 'DELETE',
  });
}

export function submitQuoteRequest(body: {
  company_id: string;
  title: string;
  scope: string;
  budget_min_cents: number;
  budget_max_cents: number;
  target_cents?: number;
  project_id?: string;
}): Promise<QuoteRequestPublic> {
  return request<QuoteRequestPublic>('/quotes/requests', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function listQuoteRequests(state?: QuoteRequestState): Promise<QuoteRequestPublic[]> {
  const query = state ? `?state=${state}` : '';
  return request<QuoteRequestPublic[]>(`/quotes/requests${query}`);
}

export function getQuoteRequest(requestId: string): Promise<QuoteRequestDetail> {
  return request<QuoteRequestDetail>(
    `/quotes/requests/${encodeURIComponent(requestId)}`
  );
}

export function counterQuoteRequest(
  requestId: string,
  targetCents: number,
  note: string
): Promise<QuoteRequestDetail> {
  return request<QuoteRequestDetail>(
    `/quotes/requests/${encodeURIComponent(requestId)}/counter`,
    { method: 'POST', body: JSON.stringify({ target_cents: targetCents, note }) }
  );
}

export function cancelQuoteRequest(
  requestId: string,
  reason: string
): Promise<QuoteRequestPublic> {
  return request<QuoteRequestPublic>(
    `/quotes/requests/${encodeURIComponent(requestId)}/cancel`,
    { method: 'POST', body: JSON.stringify({ reason }) }
  );
}

export function answerQuoteRequest(
  requestId: string,
  body: { total_cents: number; valid_days: number; gst_included: boolean; note: string }
): Promise<QuotePublic> {
  return request<QuotePublic>(
    `/quotes/requests/${encodeURIComponent(requestId)}/quotes`,
    { method: 'POST', body: JSON.stringify(body) }
  );
}

export function reviseQuote(
  quoteId: string,
  body: { total_cents: number; valid_days: number; gst_included: boolean; note: string }
): Promise<QuotePublic> {
  return request<QuotePublic>(`/quotes/${encodeURIComponent(quoteId)}/revise`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function refuseQuoteRequest(
  requestId: string,
  reason: string
): Promise<QuoteRequestPublic> {
  return request<QuoteRequestPublic>(
    `/quotes/requests/${encodeURIComponent(requestId)}/refuse`,
    { method: 'POST', body: JSON.stringify({ reason }) }
  );
}

export function acceptQuote(quoteId: string): Promise<QuotePublic> {
  return request<QuotePublic>(`/quotes/${encodeURIComponent(quoteId)}/accept`, {
    method: 'POST',
  });
}

export function declineQuote(quoteId: string, reason: string): Promise<QuotePublic> {
  return request<QuotePublic>(`/quotes/${encodeURIComponent(quoteId)}/decline`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

export function listAllCategories(): Promise<CategoryPublic[]> {
  return request<CategoryPublic[]>('/categories/all');
}

export function createCategory(name: string): Promise<CategoryPublic> {
  return request<CategoryPublic>('/categories', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
}

export function patchCategory(
  categoryId: string,
  body: { name?: string; active?: boolean }
): Promise<CategoryPublic> {
  return request<CategoryPublic>(`/categories/${encodeURIComponent(categoryId)}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
}

export function getReport(period: string, buckets: number): Promise<Report> {
  return request<Report>(`/reports?period=${period}&buckets=${buckets}`);
}

export function deleteProject(
  projectId: string
): Promise<void> {
  return request<void>(
    `/projects/${encodeURIComponent(projectId)}`,
    {
      method: 'DELETE',
    }
  );
}