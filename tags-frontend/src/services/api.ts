import { API_BASE_URL } from '../config/api';
import type {
  User, TagMember, TagEvent, TagEventDetail, Registration,
  ScoreEntry, ScoreImportResult, ScoreResolution,
  StandingEntry, HistoryEntry, Inventory,
  TransitionResponse, ImportRegistrationResult,
  MemberSearchResult, DuplicateCheckResponse, RegisterPlayerPayload,
  EventType, EventStatus, DistributionResult,
} from '../types';

// ── Fetch Wrapper ────────────────────────────────────────────────────────────

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new ApiError(body.error || res.statusText, res.status);
  }

  return res.json();
}

async function requestFormData<T>(path: string, formData: FormData): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    body: formData,
    // Don't set Content-Type — browser sets it with boundary for multipart
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new ApiError(body.error || res.statusText, res.status);
  }

  return res.json();
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export const auth = {
  me: () => request<User>('/api/auth/me'),

  login: (username: string, password: string) =>
    request<User>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  logout: () =>
    request<{ message: string }>('/api/auth/logout', { method: 'POST' }),
};

// ── Members ──────────────────────────────────────────────────────────────────

export const members = {
  list: () => request<TagMember[]>('/api/tags/members'),

  create: (data: {
    name: string;
    udisc_name?: string;
    current_tag?: number;
    email?: string;
    phone?: string;
    shipping_address?: string;
    payment_method?: string;
  }) => request<{ member_id: number; name: string; udisc_name: string | null; current_tag: number | null }>(
    '/api/tags/members',
    { method: 'POST', body: JSON.stringify(data) }
  ),

  update: (memberId: number, data: Partial<TagMember>) =>
    request<{ member_id: number; name: string }>(
      `/api/tags/members/${memberId}`,
      { method: 'PUT', body: JSON.stringify(data) }
    ),

  delete: (memberId: number) =>
    request<{ message: string }>(`/api/tags/members/${memberId}`, { method: 'DELETE' }),

  search: (query: string) =>
    request<MemberSearchResult[]>(`/api/tags/members/search?q=${encodeURIComponent(query)}`),

  checkDuplicate: (name: string, udisc_name?: string) =>
    request<DuplicateCheckResponse>('/api/tags/members/check-duplicate', {
      method: 'POST',
      body: JSON.stringify({ name, udisc_name }),
    }),

  assignTag: (memberId: number, seasonYear: number, tagNumber?: number) =>
    request<{ message: string; member_id: number; current_tag: number | null }>(
      `/api/tags/members/${memberId}/assign-tag`,
      { method: 'POST', body: JSON.stringify({ season_year: seasonYear, tag_number: tagNumber }) }
    ),

  history: (memberId: number) =>
    request<HistoryEntry[]>(`/api/tags/members/${memberId}/history`),
};

// ── Events ───────────────────────────────────────────────────────────────────

export const events = {
  list: () => request<TagEvent[]>('/api/tags/events'),

  get: (eventId: number) => request<TagEventDetail>(`/api/tags/events/${eventId}`),

  create: (data: { date: string; event_type: EventType; course?: string; notes?: string }) =>
    request<{ event_id: number; event_type: EventType; status: EventStatus }>(
      '/api/tags/events',
      { method: 'POST', body: JSON.stringify(data) }
    ),

  transition: (eventId: number, targetStatus: EventStatus, seasonYear?: number) =>
    request<TransitionResponse>(`/api/tags/events/${eventId}/transition`, {
      method: 'POST',
      body: JSON.stringify({
        target_status: targetStatus,
        season_year: seasonYear || new Date().getFullYear(),
      }),
    }),
};

// ── Registration ─────────────────────────────────────────────────────────────

export const registration = {
  register: (eventId: number, payload: RegisterPlayerPayload) =>
    request<Registration>(`/api/tags/events/${eventId}/register`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  importCsv: (eventId: number, file: File, nonPlayerDivisions?: string[]) => {
    const formData = new FormData();
    formData.append('file', file);
    if (nonPlayerDivisions) {
      nonPlayerDivisions.forEach(d => formData.append('non_player_divisions', d));
    }
    return requestFormData<ImportRegistrationResult>(
      `/api/tags/events/${eventId}/register/import`,
      formData
    );
  },

  update: (eventId: number, regId: number, data: Partial<{
    is_player: boolean;
    old_tag: number;
    is_dnf: boolean;
    is_checked_in: boolean;
  }>) => request<Registration>(
    `/api/tags/events/${eventId}/registrations/${regId}`,
    { method: 'PUT', body: JSON.stringify(data) }
  ),
};

// ── Check-in ─────────────────────────────────────────────────────────────────

export const checkin = {
  checkIn: (eventId: number, data: { member_id?: number; reg_id?: number; old_tag?: number }) =>
    request<Registration>(`/api/tags/events/${eventId}/checkin`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

// ── Scores ───────────────────────────────────────────────────────────────────

export const scores = {
  submit: (eventId: number, scoreEntries: ScoreEntry[]) =>
    request<{ message: string }>(`/api/tags/events/${eventId}/scores`, {
      method: 'POST',
      body: JSON.stringify({ scores: scoreEntries }),
    }),

  importFile: (eventId: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return requestFormData<ScoreImportResult>(
      `/api/tags/events/${eventId}/scores/import`,
      formData
    );
  },

  resolve: (eventId: number, resolutions: ScoreResolution[]) =>
    request<{ message: string }>(`/api/tags/events/${eventId}/scores/resolve`, {
      method: 'POST',
      body: JSON.stringify({ resolutions }),
    }),
};

// ── Standings ────────────────────────────────────────────────────────────────

export const standings = {
  get: () => request<StandingEntry[]>('/api/tags/standings'),
};

// ── Inventory ────────────────────────────────────────────────────────────────

export const inventory = {
  get: (year?: number) =>
    request<Inventory>(`/api/tags/inventory${year ? `?year=${year}` : ''}`),

  set: (seasonYear: number, totalTags: number) =>
    request<{ message: string; season_year: number; total_tags: number }>(
      '/api/tags/inventory',
      { method: 'POST', body: JSON.stringify({ season_year: seasonYear, total_tags: totalTags }) }
    ),

  markUnavailable: (seasonYear: number, tagNumber: number, reason?: string) =>
    request<{ message: string }>('/api/tags/inventory/unavailable', {
      method: 'POST',
      body: JSON.stringify({ season_year: seasonYear, tag_number: tagNumber, reason }),
    }),

  restoreAvailable: (seasonYear: number, tagNumber: number) =>
    request<{ message: string }>('/api/tags/inventory/unavailable', {
      method: 'DELETE',
      body: JSON.stringify({ season_year: seasonYear, tag_number: tagNumber }),
    }),
};

// ── Re-export error class ────────────────────────────────────────────────────

export { ApiError };
