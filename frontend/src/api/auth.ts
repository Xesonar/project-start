import { apiRequest } from "./client";

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export function authWithMax(initData: string): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/auth/max", {
    method: "POST",
    body: { init_data: initData },
    auth: false,
  });
}

/** Demo entry point for judges — no MAX account needed (POST /auth/demo). */
export function authDemo(): Promise<TokenResponse> {
  const storageKey = "project-start.demo-session";
  let sessionId: string | null = null;
  try {
    sessionId = window.sessionStorage.getItem(storageKey);
    if (!sessionId) {
      sessionId = globalThis.crypto?.randomUUID?.() ??
        `${Date.now()}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
      window.sessionStorage.setItem(storageKey, sessionId);
    }
  } catch {
    sessionId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }
  return apiRequest<TokenResponse>("/auth/demo", {
    method: "POST",
    body: { session_id: sessionId },
    auth: false,
  });
}
