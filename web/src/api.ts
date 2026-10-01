export type Role = "owner" | "admin" | "member" | "auditor";
export const ROLE_RANK: Record<Role, number> = { auditor: 0, member: 1, admin: 2, owner: 3 };
export const ROLE_LABEL: Record<Role, string> = {
  owner: "Owner",
  admin: "Admin",
  member: "Member",
  auditor: "Auditor (read-only)",
};

export interface OrgSummary { id: string; name: string; role: Role }
export interface Me { id: string; email: string; name: string; organisations: OrgSummary[] }
export interface Org { id: string; name: string; abn: string | null; created_at: string; role: Role }
export interface Member { user_id: string; email: string; name: string; role: Role; joined_at: string }
export interface Invitation { id: string; email: string; role: Role; created_at: string; expires_at: string }
export interface InvitationPreview { organisation: string; email: string; role: Role; expires_at: string }
export interface MyInvitation { id: string; organisation: string; role: Role; expires_at: string }

// Essential Eight
export type E8Answer = "yes" | "partly" | "no" | "na";
export const E8_ANSWER_LABEL: Record<E8Answer, string> = { yes: "Yes", partly: "Partly", no: "No", na: "N/A" };
export interface E8Strategy { code: string; name: string; priority: number; summary: string }
export interface E8Requirement {
  id: string; strategy: string; level: number; until: number | null; key: string;
  effort: "low" | "medium" | "high"; title: string; text: string;
}
export interface E8Content {
  version: string; attribution: string; source_url: string; licence_url: string;
  strategies: E8Strategy[]; requirements: E8Requirement[];
}
export interface E8AnswerOut { key: string; answer: E8Answer; note: string; answered_by: string | null; answered_at: string }
export interface E8StrategyScore { code: string; level: number; next_level: number | null; next_met: number; next_total: number }
export interface E8Score { overall_level: number; strategies: E8StrategyScore[] }
export interface E8Snapshot {
  id: string; content_version: string; target_level: number; overall_level: number; score: E8Score;
  created_by: string | null; created_at: string;
}
export interface E8Assessment {
  content_version: string; target_level: number; answers: E8AnswerOut[]; score: E8Score; last_snapshot: E8Snapshot | null;
}
export interface E8PlanItem {
  key: string; level: number; strategies: string[]; title: string; text: string;
  effort: "low" | "medium" | "high"; answer: E8Answer | null; in_target: boolean;
}
export interface E8Plan { target_level: number; items: E8PlanItem[] }

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export type TokenSource = () => Promise<string>;

export async function api<T>(path: string, token: TokenSource | null, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${await token()}`;
  const res = await fetch(`/api${path}`, { ...init, headers: { ...headers, ...(init.headers as object) } });
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(body.detail) ? body.detail.map((d: { msg: string }) => d.msg).join("; ") : body.detail;
    throw new ApiError(res.status, detail || `Request failed (${res.status})`);
  }
  return body as T;
}
