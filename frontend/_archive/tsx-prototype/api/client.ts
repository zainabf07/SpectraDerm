import type { Action, Analysis, ApiErrorEnvelope, History, ImageArtifact, Report, Scan, ScanList, User, ReferralRequest } from "../types/api";
const base = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
export class ApiError extends Error { constructor(public status: number, public code = "REQUEST_FAILED", message = "We couldn't complete that request right now.") { super(message); } }
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  try { const multipart = typeof FormData !== "undefined" && init.body instanceof FormData; const response = await fetch(`${base}${path}`, { headers: { ...(multipart ? {} : { "Content-Type": "application/json" }), ...init.headers }, ...init });
    if (response.status === 204) return undefined as T;
    const body = await response.json().catch(() => ({}));
    if (!response.ok) { const error = (body as ApiErrorEnvelope).error; throw new ApiError(response.status, error?.code, error?.message || "We couldn't complete that request right now."); }
    return body as T;
  } catch (error) { if (error instanceof ApiError) throw error; throw new ApiError(0, "NETWORK_ERROR", "We couldn't reach SpectraDerm. Please check your connection and try again."); }
}
const json = (method: string, value?: unknown) => ({ method, body: value === undefined ? undefined : JSON.stringify(value) });
export const api = {
  health: () => request<{status:string}>("/health"), createUser: (general_consent=false, location_consent=false) => request<User>("/api/v1/users", json("POST", {general_consent, location_consent})),
  getUser: (id:string) => request<User>(`/api/v1/users/${id}`), updateConsent: (id:string, value: Partial<Pick<User,"general_consent"|"location_consent">>) => request<User>(`/api/v1/users/${id}/consent`, json("PATCH", value)),
  uploadImage: (userId:string, file:File) => { const form = new FormData(); form.append("file", file); return request<ImageArtifact>(`/api/v1/users/${userId}/image-artifacts`, {method:"POST", body:form}); },
  createScan: (userId:string, image_reference:string) => request<Scan>(`/api/v1/users/${userId}/scans`, json("POST", {image_reference})), listScans: (userId:string) => request<ScanList>(`/api/v1/users/${userId}/scans`),
  getScan: (scanId:string,userId:string) => request<Scan>(`/api/v1/scans/${scanId}?user_id=${encodeURIComponent(userId)}`), deleteScan: (scanId:string,userId:string) => request<void>(`/api/v1/scans/${scanId}?user_id=${encodeURIComponent(userId)}`, {method:"DELETE"}),
  analyze: (scanId:string,userId:string,input:Record<string,unknown>={}) => request<Analysis>(`/api/v1/scans/${scanId}/analyze?user_id=${encodeURIComponent(userId)}`,json("POST",{input})),
  history: (userId:string) => request<History>(`/api/v1/users/${userId}/history`), timeline: (userId:string) => request<History>(`/api/v1/users/${userId}/timeline`), report: (scanId:string,userId:string) => request<Report>(`/api/v1/scans/${scanId}/report?user_id=${encodeURIComponent(userId)}`),
  products: (scanId:string,userId:string) => request<Action>(`/api/v1/scans/${scanId}/products?user_id=${encodeURIComponent(userId)}`), referrals: (scanId:string,userId:string,location:ReferralRequest) => request<Action>(`/api/v1/scans/${scanId}/referrals?user_id=${encodeURIComponent(userId)}`,json("POST",location))
};
