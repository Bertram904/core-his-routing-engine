/**
 * Auth API — LoginPage, DashboardPage, AppShell
 * POST /api/v1/auth/login
 * GET  /api/v1/auth/me
 */
import { API_ENDPOINTS } from "@/api/endpoints";
import { httpRequest } from "@/api/httpClient";
import type {
  LoginRequest,
  TokenResponse,
  UserProfile,
} from "@/types/api.types";

export async function loginApi(payload: LoginRequest): Promise<TokenResponse> {
  return httpRequest<TokenResponse>(API_ENDPOINTS.auth.login, {
    method: "POST",
    body: payload,
  });
}

export async function getCurrentUserApi(token: string): Promise<UserProfile> {
  return httpRequest<UserProfile>(API_ENDPOINTS.auth.me, { token });
}

export async function clinicalDemoApi(
  token: string,
): Promise<{ message: string; username: string }> {
  return httpRequest(API_ENDPOINTS.auth.clinicalDemo, { token });
}
