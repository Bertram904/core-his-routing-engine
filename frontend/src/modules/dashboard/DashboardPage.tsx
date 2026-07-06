import { useEffect, useState } from "react";

import { clinicalDemoApi } from "@/api/auth.api";
import { API_ENDPOINTS } from "@/api/endpoints";
import { ApiError } from "@/api/httpClient";
import { useAuth } from "@/auth/AuthContext";
import { canAccessModule } from "@/constants/scopes";
import { ApiCallBadge } from "@/components/ui/ApiCallBadge";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBanner } from "@/components/ui/StatusBanner";

export function DashboardPage() {
  const { user, token } = useAuth();
  const [demoMessage, setDemoMessage] = useState<string | null>(null);
  const [demoError, setDemoError] = useState<string | null>(null);

  const scopes = user?.scopes ?? [];

  useEffect(() => {
    setDemoMessage(null);
    setDemoError(null);
  }, [user?.username]);

  async function runClinicalDemo() {
    if (!token) {
      return;
    }
    setDemoError(null);
    try {
      const result = await clinicalDemoApi(token);
      setDemoMessage(result.message);
    } catch (error) {
      setDemoError(
        error instanceof ApiError ? error.message : "Không gọi được demo API",
      );
    }
  }

  return (
    <div>
      <PageHeader
        moduleLabel="Dashboard"
        title="Tổng quan hệ thống"
        subtitle="Xem quyền truy cập và điều hướng tới module theo scope RBAC."
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="card">
          <h2 className="text-lg font-semibold">Thông tin phiên đăng nhập</h2>
          <ApiCallBadge
            method="GET"
            path={API_ENDPOINTS.auth.me}
            description="DashboardPage load user + scopes sau khi đăng nhập"
          />
          <dl className="mt-4 space-y-3 text-sm">
            <div className="flex justify-between border-b border-surface-100 pb-2">
              <dt className="text-slate-500">Username</dt>
              <dd className="font-semibold">{user?.username}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Scopes</dt>
              <dd className="mt-2 flex flex-wrap gap-2">
                {scopes.map((scope) => (
                  <span
                    key={scope}
                    className="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700"
                  >
                    {scope}
                  </span>
                ))}
              </dd>
            </div>
          </dl>
        </section>

        <section className="card">
          <h2 className="text-lg font-semibold">Module được phép truy cập</h2>
          <ul className="mt-4 space-y-3 text-sm">
            <li className="flex items-center justify-between rounded-lg bg-surface-50 px-3 py-2">
              <span>Tiếp đón (Reception)</span>
              <span className="font-semibold text-emerald-600">
                {canAccessModule(scopes, "reception") ? "Có" : "Không"}
              </span>
            </li>
            <li className="flex items-center justify-between rounded-lg bg-surface-50 px-3 py-2">
              <span>Lâm sàng (Clinical)</span>
              <span className="font-semibold text-emerald-600">
                {canAccessModule(scopes, "clinical") ? "Có" : "Không"}
              </span>
            </li>
          </ul>
        </section>
      </div>

      {canAccessModule(scopes, "clinical") ? (
        <section className="card mt-6">
          <h2 className="text-lg font-semibold">Kiểm tra RBAC demo</h2>
          <ApiCallBadge
            method="GET"
            path={API_ENDPOINTS.auth.clinicalDemo}
            description="Chỉ user có scope write:clinical_record mới gọi được"
          />
          <button type="button" className="btn-primary mt-2" onClick={runClinicalDemo}>
            Gọi clinical-records/demo
          </button>
          {demoMessage ? (
            <div className="mt-3">
              <StatusBanner type="success" message={demoMessage} />
            </div>
          ) : null}
          {demoError ? (
            <div className="mt-3">
              <StatusBanner type="error" message={demoError} />
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
