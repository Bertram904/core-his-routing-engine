/**
 * API endpoint registry.
 * Mỗi màn hình import path từ đây — nhìn một chỗ biết toàn bộ contract.
 */
import { API_PREFIX } from "@/config/apiConfig";

export const API_ENDPOINTS = {
  auth: {
    /** LoginPage → đăng nhập, lấy JWT */
    login: `${API_PREFIX}/auth/login`,
    /** DashboardPage, AppShell → hiển thị user + scopes */
    me: `${API_PREFIX}/auth/me`,
    /** DashboardPage (demo RBAC) */
    clinicalDemo: `${API_PREFIX}/auth/clinical-records/demo`,
  },
  reception: {
    /** ReceptionDeskPage → tra cứu CCCD */
    autoPopulate: `${API_PREFIX}/reception/auto-populate`,
    /** ReceptionDeskPage → tiếp nhận + routing */
    intake: `${API_PREFIX}/reception/intake`,
  },
  clinical: {
    /** ClinicalWorkspacePage, ReceptionDeskPage → danh sách workflow */
    workflows: `${API_PREFIX}/workflows`,
    /** ClinicalWorkspacePage → tạo hồ sơ lâm sàng */
    createRecord: (workflowId: number) =>
      `${API_PREFIX}/workflows/${workflowId}/record`,
    /** ClinicalWorkspacePage → xuất PDF */
    exportPdf: (workflowId: number) =>
      `${API_PREFIX}/workflows/${workflowId}/export-pdf`,
  },
} as const;
