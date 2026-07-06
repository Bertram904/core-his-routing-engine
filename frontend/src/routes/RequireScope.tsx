import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import type { AppModule } from "@/constants/scopes";

interface RequireScopeProps {
  module: AppModule;
}

export function RequireScope({ module }: RequireScopeProps) {
  const { canAccess } = useAuth();

  if (!canAccess(module)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
