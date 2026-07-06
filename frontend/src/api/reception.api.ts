/**
 * Reception API — ReceptionDeskPage
 * GET  /api/v1/reception/auto-populate
 * POST /api/v1/reception/intake
 */
import { API_ENDPOINTS } from "@/api/endpoints";
import { httpRequest } from "@/api/httpClient";
import type {
  PatientAutoPopulateResult,
  ReceptionIntakeRequest,
  ReceptionIntakeResult,
} from "@/types/api.types";

export async function autoPopulateApi(
  token: string,
  identityNumber: string,
): Promise<PatientAutoPopulateResult> {
  return httpRequest<PatientAutoPopulateResult>(
    API_ENDPOINTS.reception.autoPopulate,
    {
      token,
      query: { identity_number: identityNumber },
    },
  );
}

export async function receptionIntakeApi(
  token: string,
  payload: ReceptionIntakeRequest,
): Promise<ReceptionIntakeResult> {
  return httpRequest<ReceptionIntakeResult>(API_ENDPOINTS.reception.intake, {
    method: "POST",
    token,
    body: payload,
  });
}
