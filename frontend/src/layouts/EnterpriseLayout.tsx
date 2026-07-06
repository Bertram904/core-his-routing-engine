import { Outlet } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { SidebarNav } from "@/layouts/SidebarNav";

export function EnterpriseLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-screen bg-surface-50">
      <aside className="flex w-64 flex-col bg-surface-900 text-white">
        <div className="border-b border-surface-800 px-5 py-6">
          <p className="text-xs font-semibold uppercase tracking-widest text-brand-100">
            Core HIS
          </p>
          <h1 className="mt-1 text-lg font-bold">Hospital System</h1>
          <p className="mt-1 text-xs text-slate-400">Enterprise Portal</p>
        </div>

        <div className="flex-1 px-3 py-4">
          <SidebarNav />
        </div>

        <div className="border-t border-surface-800 px-4 py-4">
          <p className="text-sm font-semibold">{user?.username}</p>
          <p className="mt-1 text-xs text-slate-400">
            {user?.scopes.join(" · ")}
          </p>
          <button
            type="button"
            onClick={logout}
            className="mt-3 w-full rounded-lg border border-surface-700 px-3 py-2 text-xs font-semibold text-slate-300 transition hover:bg-surface-800"
          >
            Đăng xuất
          </button>
        </div>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="border-b border-surface-200 bg-white px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-500">Bệnh viện mô phỏng VDT 2026</p>
              <p className="text-sm font-medium text-surface-900">
                Hệ thống thông tin bệnh viện
              </p>
            </div>
            <a
              href="/docs"
              target="_blank"
              rel="noreferrer"
              className="text-xs font-semibold text-brand-600 hover:text-brand-700"
            >
              OpenAPI /docs
            </a>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto px-8 py-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
