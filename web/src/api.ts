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
