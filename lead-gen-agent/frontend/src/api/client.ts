// ---------------------------------------------------------------------------
// TypeScript types matching the FastAPI response models
// ---------------------------------------------------------------------------

export interface Stats {
  total_leads: number;
  total_runs: number;
  hot_leads: number;
  warm_leads: number;
  cold_leads: number;
  leads_with_email: number;
  leads_with_verified_email: number;
  leads_with_outreach: number;
  average_score: number | null;
  scrape_cache_entries: number;
}

export interface RunConfig {
  industry: string;
  titles: string[];
  location: string;
  limit: number;
  keywords?: string[];
  company_size?: string;
  sender_name?: string;
  sender_company?: string;
}

export interface RunSummary {
  total_leads: number;
  hot: number;
  warm: number;
  cold: number;
  with_outreach: number;
}

export interface Run {
  id: string;
  created_at: string;
  status: "running" | "done" | "failed";
  config: RunConfig;
  summary?: RunSummary;
  leads?: Lead[];
}

export type Tier = "Hot" | "Warm" | "Cold";

export interface Lead {
  id: string;
  run_id: string;
  created_at: string;
  name: string;
  title: string;
  company: string;
  website: string;
  location: string;
  linkedin_url: string;
  source: string;
  email: string;
  email_verified: number;
  email_source: string;
  company_summary: string;
  pain_points: string[];
  tech_signals: string[];
  score: number;
  tier: Tier;
  score_reasoning: string;
  scored_at: string;
  email_subject: string;
  email_body: string;
  outreach_at: string;
  enriched_at: string;
}

export interface RunsResponse {
  runs: Run[];
  count: number;
}

export interface RunLeadsResponse {
  run_id: string;
  leads: Lead[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface LeadsResponse {
  leads: Lead[];
  count: number;
  limit: number;
  offset: number;
}

export interface StartRunRequest {
  industry: string;
  titles: string[];
  location: string;
  keywords: string[];
  company_size?: string;
  limit: number;
  sender_name: string;
  sender_company: string;
  skip_outreach: boolean;
  webhook_url?: string;
}

export interface StartRunResponse {
  run_id: string;
  status: string;
  message: string;
}

export interface ExportRequest {
  run_id?: string;
  tier?: string;
  min_score?: number;
  format: "csv" | "json";
}

// ---------------------------------------------------------------------------
// Fetch helper
// ---------------------------------------------------------------------------

const BASE = import.meta.env.VITE_API_URL ?? "";
const API_KEY = import.meta.env.VITE_API_KEY ?? "";

async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
    ...(opts?.headers as Record<string, string>),
  };
  const res = await fetch(`${BASE}${path}`, { ...opts, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((err as { detail?: string }).detail ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// API surface
// ---------------------------------------------------------------------------

export const api = {
  getStats: () => request<Stats>("/api/stats"),

  getRuns: (limit = 50) =>
    request<RunsResponse>(`/api/runs?limit=${limit}`),

  getRun: (id: string, includeLeads = false) =>
    request<Run>(`/api/runs/${id}?include_leads=${includeLeads}`),

  getRunLeads: (
    id: string,
    params: { limit?: number; offset?: number; tier?: string } = {},
  ) => {
    const q = new URLSearchParams();
    if (params.limit !== undefined) q.set("limit", String(params.limit));
    if (params.offset !== undefined) q.set("offset", String(params.offset));
    if (params.tier) q.set("tier", params.tier);
    return request<RunLeadsResponse>(`/api/runs/${id}/leads?${q}`);
  },

  startRun: (data: StartRunRequest) =>
    request<StartRunResponse>("/api/runs", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getLeads: (params: {
    tier?: string;
    min_score?: number;
    limit?: number;
    offset?: number;
  } = {}) => {
    const q = new URLSearchParams();
    if (params.tier) q.set("tier", params.tier);
    if (params.min_score !== undefined) q.set("min_score", String(params.min_score));
    if (params.limit !== undefined) q.set("limit", String(params.limit));
    if (params.offset !== undefined) q.set("offset", String(params.offset));
    return request<LeadsResponse>(`/api/leads?${q}`);
  },

  getLead: (id: string) => request<Lead>(`/api/leads/${id}`),

  exportLeads: async (data: ExportRequest): Promise<void> => {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
    };
    const res = await fetch(`${BASE}/api/leads/export`, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Export failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = data.format === "csv" ? "leads.csv" : "leads.json";
    a.click();
    URL.revokeObjectURL(url);
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

export function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
