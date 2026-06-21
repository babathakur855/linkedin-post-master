const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8040";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Types ──────────────────────────────────────────────────────────────────────

export interface Niche {
  id: number;
  name: string;
  description: string;
  keywords: string[];
  frequency: string;
  schedule_day: number | null;
  schedule_time: string;
  publish_format: string;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Blog {
  id: number;
  niche_id: number;
  niche_name?: string;
  topic: string;
  title: string;
  status: string;
  publish_format: string;
  revision_count: number;
  published_url: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
  // detail fields
  content_markdown?: string;
  linkedin_post?: string;
  linkedin_article_title?: string;
  linkedin_article_body?: string;
  research_summary?: string;
  logs?: { phase: string; message: string; created_at: string }[];
  revisions?: { id: number; revision_number: number; changes_requested: string; created_at: string }[];
}

export interface Stats {
  total: number;
  published: number;
  pending_review: number;
  drafts: number;
}

export interface Settings {
  smtp_host?: string;
  smtp_port?: string;
  smtp_user?: string;
  smtp_password?: string;
  from_email?: string;
  imap_host?: string;
  imap_port?: string;
  review_email?: string;
  frontend_url?: string;
  linkedin_client_id?: string;
  linkedin_client_secret?: string;
}

// ── Niches ─────────────────────────────────────────────────────────────────────

export const getNiches = () => request<Niche[]>("/api/niches/");
export const createNiche = (body: Partial<Niche>) =>
  request<Niche>("/api/niches/", { method: "POST", body: JSON.stringify(body) });
export const updateNiche = (id: number, body: Partial<Niche>) =>
  request<Niche>(`/api/niches/${id}`, { method: "PUT", body: JSON.stringify(body) });
export const deleteNiche = (id: number) =>
  request<void>(`/api/niches/${id}`, { method: "DELETE" });

// ── Blogs ──────────────────────────────────────────────────────────────────────

export const getBlogs = (params?: { status?: string; niche_id?: number }) => {
  const qs = params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : "";
  return request<Blog[]>(`/api/blogs/${qs}`);
};
export const getBlogStats = () => request<Stats>("/api/blogs/stats");
export const getBlog = (id: number) => request<Blog>(`/api/blogs/${id}`);
export const generateBlog = (niche_id: number, publish_format?: string) =>
  request<{ blog_id: number; status: string }>("/api/blogs/generate", {
    method: "POST",
    body: JSON.stringify({ niche_id, publish_format }),
  });
export const reviseBlog = (id: number, changes: string) =>
  request<unknown>(`/api/blogs/${id}/revise`, {
    method: "POST",
    body: JSON.stringify({ changes }),
  });
export const approveBlog = (id: number) =>
  request<unknown>(`/api/blogs/${id}/approve`, { method: "POST" });
export const deleteBlog = (id: number) =>
  request<void>(`/api/blogs/${id}`, { method: "DELETE" });

// ── Settings ───────────────────────────────────────────────────────────────────

export const getSettings = () => request<Settings>("/api/settings/");
export const updateSettings = (body: Partial<Settings>) =>
  request<{ status: string }>("/api/settings/", { method: "PUT", body: JSON.stringify(body) });
export const getLinkedInStatus = () =>
  request<{ connected: boolean; person_id: string; expires_at: string; expired: boolean; client_id_set: boolean }>(
    "/api/settings/linkedin/status"
  );
export const getLinkedInAuthUrl = () =>
  request<{ url: string; redirect_uri: string }>("/api/settings/linkedin/auth-url");
export const linkedInCallback = (code: string, redirect_uri: string) =>
  request<unknown>("/api/settings/linkedin/callback", {
    method: "POST",
    body: JSON.stringify({ code, redirect_uri }),
  });

// ── WebSocket ──────────────────────────────────────────────────────────────────

export function createBlogWebSocket(
  blogId: number,
  onMessage: (data: { type: string; phase?: string; message?: string }) => void
): WebSocket {
  const wsUrl = (API_URL || "http://localhost:8040").replace(/^http/, "ws");
  const ws = new WebSocket(`${wsUrl}/ws/${blogId}`);
  ws.onmessage = (e) => {
    try {
      onMessage(JSON.parse(e.data));
    } catch {}
  };
  return ws;
}
