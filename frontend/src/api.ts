import type {
  AccountPublic,
  HealthResponse,
  LoginRequest,
  RegisterRequest,
  Status,
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