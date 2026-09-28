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
