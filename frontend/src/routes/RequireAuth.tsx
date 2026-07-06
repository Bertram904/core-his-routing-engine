import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";

export function RequireAuth() {
  const { token, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">
        Đang xác thực phiên đăng nhập...
      </div>
    );
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
