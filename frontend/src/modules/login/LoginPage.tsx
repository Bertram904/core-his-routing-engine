import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";

import { API_ENDPOINTS } from "@/api/endpoints";
import { ApiError } from "@/api/httpClient";
import { useAuth } from "@/auth/AuthContext";
import { ApiCallBadge } from "@/components/ui/ApiCallBadge";
import { StatusBanner } from "@/components/ui/StatusBanner";

const DEMO_ACCOUNTS = [
  {
    username: "dr_smith",
    password: "Secret123!",
    role: "Bác sĩ — Tiếp đón + Lâm sàng",
  },
  {
    username: "recep_clerk",
    password: "Secret123!",
    role: "Lễ tân — Chỉ Tiếp đón",
  },
];

export function LoginPage() {
  const { login, token } = useAuth();
  const [username, setUsername] = useState("dr_smith");
  const [password, setPassword] = useState("Secret123!");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (token) {
    return <Navigate to="/dashboard" replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login({ username, password });
    } catch (submitError) {
      const message =
        submitError instanceof ApiError
          ? submitError.message
          : "Đăng nhập thất bại";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  function fillDemoAccount(accountUsername: string, accountPassword: string) {
    setUsername(accountUsername);
    setPassword(accountPassword);
  }

  return (
    <div className="flex min-h-screen">
      <section className="hidden w-1/2 flex-col justify-between bg-surface-900 p-12 text-white lg:flex">
        <div>
          <p className="text-sm font-semibold uppercase tracking-widest text-brand-100">
            Core HIS
          </p>
          <h1 className="mt-4 text-4xl font-bold leading-tight">
            Enterprise Hospital Portal
          </h1>
          <p className="mt-4 max-w-md text-slate-300">
            Giao diện phân quyền theo scope RBAC. Mỗi màn hình map rõ endpoint
            API tương ứng để dễ kiểm thử luồng nghiệp vụ.
          </p>
        </div>
        <div className="space-y-3 text-sm text-slate-400">
          <p>Luồng nghiệp vụ: Đăng nhập → Tiếp đón → Routing → Lâm sàng → PDF</p>
        </div>
      </section>

      <section className="flex flex-1 items-center justify-center p-8">
        <div className="w-full max-w-md">
          <h2 className="text-2xl font-bold text-surface-900">Đăng nhập</h2>
          <p className="mt-2 text-sm text-slate-500">
            Chọn tài khoản demo theo vai trò để test phân màn hình.
          </p>

          <ApiCallBadge
            method="POST"
            path={API_ENDPOINTS.auth.login}
            description="LoginPage gọi API này để lấy JWT access_token"
          />

          {error ? (
            <div className="mb-4">
              <StatusBanner type="error" message={error} />
            </div>
          ) : null}

          <form onSubmit={handleSubmit} className="card space-y-4">
            <div>
              <label className="label-text" htmlFor="username">
                Tên đăng nhập
              </label>
              <input
                id="username"
                className="input-field"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                autoComplete="username"
              />
            </div>
            <div>
              <label className="label-text" htmlFor="password">
                Mật khẩu
              </label>
              <input
                id="password"
                type="password"
                className="input-field"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
              />
            </div>
            <button type="submit" className="btn-primary w-full" disabled={isSubmitting}>
              {isSubmitting ? "Đang đăng nhập..." : "Đăng nhập"}
            </button>
          </form>

          <div className="mt-6 space-y-2">
            <p className="text-xs font-semibold uppercase text-slate-500">
              Tài khoản demo
            </p>
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.username}
                type="button"
                onClick={() =>
                  fillDemoAccount(account.username, account.password)
                }
                className="w-full rounded-lg border border-surface-200 bg-white px-4 py-3 text-left text-sm transition hover:border-brand-500"
              >
                <span className="font-semibold">{account.username}</span>
                <span className="mt-1 block text-xs text-slate-500">
                  {account.role}
                </span>
              </button>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
