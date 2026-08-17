// ── Auth & User ──────────────────────────────────────────────────────────────

export interface User {
  user_id: number;
  username: string;
  role: 'admin' | 'director' | 'Viewer';
}

// ── Members ──────────────────────────────────────────────────────────────────

export interface TagMember {
  member_id: number;
  name: string;
  udisc_name: string | null;
  current_tag: number | null;
  is_active: boolean;
  // PII fields — only present for admin
  email?: string;
  phone?: string;
  shipping_address?: string;
  payment_method?: string;
}

export interface MemberSearchResult {
  member_id: number;
  name: string;
  udisc_name: string | null;
  current_tag: number | null;
}

export interface DuplicateCheckResponse {
  is_duplicate: boolean;
  candidates: MemberSearchResult[];
}

// ── Events ───────────────────────────────────────────────────────────────────

export type EventType = 'annual' | 'monthly';
export type EventStatus = 'pending' | 'scheduled' | 'in_progress' | 'complete';

export interface TagEvent {
  event_id: number;
  event_type: EventType;
  date: string; // ISO date
  course: string | null;
  status: EventStatus;
  notes: string | null;
  participant_count?: number;
}

export interface TagEventDetail extends TagEvent {
  registrations: Registration[];
}

// ── Registrations ────────────────────────────────────────────────────────────

export interface Registration {
  reg_id: number;
  member_id: number;
  name: string;
  udisc_name: string | null;
  is_player: boolean;
  is_checked_in: boolean;
  is_dnf: boolean;
  old_tag: number | null;
  round_score: number | null;
  new_tag: number | null;
  position: number | null;
}

export interface RegisterPlayerPayload {
  member_id: number;
  is_player?: boolean;
  is_same_day?: boolean;
  old_tag?: number | null;
}

// ── Scores ───────────────────────────────────────────────────────────────────

export interface ScoreEntry {
  member_id: number;
  round_score: number;
}

export interface ScoreImportResult {
  applied: number;
  matched: MatchedScore[];
  unmatched: UnmatchedScore[];
  needs_resolution: boolean;
}

export interface MatchedScore {
  member_id: number;
  reg_id: number;
  name: string;
  udisc_name: string;
  round_score: number;
}

export interface UnmatchedScore {
  import_name: string;
  round_score: number;
  candidates: { member_id: number; reg_id: number; name: string; udisc_name: string | null }[];
}

export interface ScoreResolution {
  reg_id: number;
  round_score: number;
}

// ── Distribution Results ─────────────────────────────────────────────────────

export interface DistributionResult {
  member_id: number;
  name: string;
  old_tag: number | null;
  new_tag: number;
  round_score: number | null;
  is_dnf: boolean;
  position: number;
}

// ── Standings ────────────────────────────────────────────────────────────────

export interface StandingEntry {
  member_id: number;
  name: string;
  udisc_name: string | null;
  current_tag: number;
}

// ── History ──────────────────────────────────────────────────────────────────

export interface HistoryEntry {
  history_id: number;
  event_id: number;
  date: string;
  course: string | null;
  event_type: EventType;
  old_tag: number | null;
  new_tag: number;
  round_score: number | null;
  is_dnf: boolean;
  position: number | null;
}

// ── Inventory ────────────────────────────────────────────────────────────────

export interface Inventory {
  season_year: number;
  total_tags: number;
  available_tags: number[];
  available_count: number;
  unavailable_tags: UnavailableTag[];
}

export interface UnavailableTag {
  tag_number: number;
  reason: string | null;
}

// ── State Transitions ────────────────────────────────────────────────────────

export interface TransitionResponse {
  message: string;
  status: EventStatus;
  details?: {
    dnf_players: { member_id: number; name: string; old_tag: number | null }[];
    non_player_assignments: { member_id: number; name: string; new_tag: number; previous_tag: number | null }[];
  };
  results?: DistributionResult[];
}

// ── Registration Import ──────────────────────────────────────────────────────

export interface ImportRegistrationResult {
  created_members: number;
  registered: number;
  skipped: number;
  details: {
    new_members: { member_id: number; name: string }[];
    registrations: { member_id: number; name: string; is_player: boolean; old_tag: number | null }[];
    skipped: { name: string; reason: string }[];
  };
}
