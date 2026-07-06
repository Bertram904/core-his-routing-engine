/** Permission scopes mirrored from backend RBAC. */

export const SCOPES = {
  READ_PATIENT: "read:patient",
  WRITE_CLINICAL: "write:clinical_record",
} as const;

export type Scope = (typeof SCOPES)[keyof typeof SCOPES];

/** Navigation modules mapped to required scopes. */
export const MODULE_ACCESS = {
  dashboard: [] as Scope[],
  reception: [SCOPES.READ_PATIENT] as Scope[],
  clinical: [SCOPES.WRITE_CLINICAL] as Scope[],
} as const;

export type AppModule = keyof typeof MODULE_ACCESS;

export function hasScope(userScopes: string[], required: Scope): boolean {
  return userScopes.includes(required);
}

export function canAccessModule(
  userScopes: string[],
  module: AppModule,
): boolean {
  const requiredScopes = MODULE_ACCESS[module];
  if (requiredScopes.length === 0) {
    return true;
  }
  return requiredScopes.some((scope) => hasScope(userScopes, scope));
}
