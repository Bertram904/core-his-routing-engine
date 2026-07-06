/**
 * Clinical API — ClinicalWorkspacePage
 * GET  /api/v1/workflows
 * POST /api/v1/workflows/{id}/record
 * GET  /api/v1/workflows/{id}/export-pdf
 */
import { API_ENDPOINTS } from "@/api/endpoints";
import { httpDownload, httpRequest } from "@/api/httpClient";
import type {
  ClinicalRecordRequest,
  ClinicalRecordResponse,
  WorkflowListItem,
} from "@/types/api.types";

export async function listWorkflowsApi(
  token: string,
): Promise<WorkflowListItem[]> {
  return httpRequest<WorkflowListItem[]>(API_ENDPOINTS.clinical.workflows, {
    token,
  });
}

export async function createClinicalRecordApi(
  token: string,
  workflowId: number,
  payload: ClinicalRecordRequest,
): Promise<ClinicalRecordResponse> {
  return httpRequest<ClinicalRecordResponse>(
    API_ENDPOINTS.clinical.createRecord(workflowId),
    {
      method: "POST",
      token,
      body: payload,
    },
  );
}

export async function exportWorkflowPdfApi(
  token: string,
  workflowId: number,
): Promise<void> {
  return httpDownload(
    API_ENDPOINTS.clinical.exportPdf(workflowId),
    token,
    `workflow-${workflowId}-clinical-report.pdf`,
  );
}
