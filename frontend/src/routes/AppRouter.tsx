import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider } from "@/auth/AuthContext";
import { EnterpriseLayout } from "@/layouts/EnterpriseLayout";
import { ClinicalWorkspacePage } from "@/modules/clinical/ClinicalWorkspacePage";
import { DashboardPage } from "@/modules/dashboard/DashboardPage";
import { LoginPage } from "@/modules/login/LoginPage";
import { ReceptionDeskPage } from "@/modules/reception/ReceptionDeskPage";
import { RequireAuth } from "@/routes/RequireAuth";
import { RequireScope } from "@/routes/RequireScope";

export function AppRouter() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route element={<RequireAuth />}>
            <Route element={<EnterpriseLayout />}>
              <Route path="/dashboard" element={<DashboardPage />} />

              <Route element={<RequireScope module="reception" />}>
                <Route path="/reception" element={<ReceptionDeskPage />} />
              </Route>

              <Route element={<RequireScope module="clinical" />}>
                <Route path="/clinical" element={<ClinicalWorkspacePage />} />
              </Route>
            </Route>
          </Route>

          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
