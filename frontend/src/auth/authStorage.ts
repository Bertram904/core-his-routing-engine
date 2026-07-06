const TOKEN_STORAGE_KEY = "core_his_access_token";

export function saveAccessToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function loadAccessToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function clearAccessToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}
