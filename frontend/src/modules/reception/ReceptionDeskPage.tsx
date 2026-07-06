import { FormEvent, useState } from "react";

import { API_ENDPOINTS } from "@/api/endpoints";
import { ApiError } from "@/api/httpClient";
import {
  autoPopulateApi,
  receptionIntakeApi,
} from "@/api/reception.api";
import { useAuth } from "@/auth/AuthContext";
import { ApiCallBadge } from "@/components/ui/ApiCallBadge";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBanner } from "@/components/ui/StatusBanner";
import type {
  PatientAutoPopulateResult,
  ReceptionIntakeResult,
} from "@/types/api.types";

const DEFAULT_IDENTITY = "001234567890";

export function ReceptionDeskPage() {
  const { token } = useAuth();
  const [identityNumber, setIdentityNumber] = useState(DEFAULT_IDENTITY);
  const [department, setDepartment] = useState("emergency");
  const [autoResult, setAutoResult] =
    useState<PatientAutoPopulateResult | null>(null);
  const [intakeResult, setIntakeResult] =
    useState<ReceptionIntakeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleAutoPopulate(event: FormEvent) {
    event.preventDefault();
    if (!token) {
      return;
    }

    setError(null);
    setIsLoading(true);
    try {
      const result = await autoPopulateApi(token, identityNumber.trim());
      setAutoResult(result);
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "Tra cứu thất bại",
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function handleIntake(event: FormEvent) {
    event.preventDefault();
    if (!token) {
      return;
    }

    setError(null);
    setIsLoading(true);
    try {
      const result = await receptionIntakeApi(token, {
        identity_number: identityNumber.trim(),
        routing_context: {
          source_stage: "registration",
          patient_id: autoResult?.patient_id ?? undefined,
          department,
        },
      });
      setIntakeResult(result);
      setAutoResult(result.auto_populate);
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "Tiếp nhận thất bại",
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div>
      <PageHeader
        moduleLabel="Reception · read:patient"
        title="Quầy tiếp đón"
        subtitle="Tra cứu bệnh nhân theo CCCD và chạy dynamic routing engine."
      />

      {error ? (
        <div className="mb-4">
          <StatusBanner type="error" message={error} />
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="card">
          <h2 className="text-lg font-semibold">1. Auto-populate bệnh nhân</h2>
          <ApiCallBadge
            method="GET"
            path={`${API_ENDPOINTS.reception.autoPopulate}?identity_number={cccd}`}
            description="ReceptionDeskPage — tra cứu demographics theo số CCCD"
          />

          <form onSubmit={handleAutoPopulate} className="space-y-4">
            <div>
              <label className="label-text" htmlFor="identity">
                Số CCCD / CMND
              </label>
              <input
                id="identity"
                className="input-field"
                value={identityNumber}
                onChange={(event) => setIdentityNumber(event.target.value)}
              />
            </div>
            <button type="submit" className="btn-primary" disabled={isLoading}>
              Tra cứu
            </button>
          </form>

          {autoResult ? (
            <div className="mt-4 rounded-lg bg-surface-50 p-4 text-sm">
              <p>
                <strong>Found:</strong> {autoResult.found ? "Có" : "Không"}
              </p>
              {autoResult.found ? (
                <>
                  <p>
                    <strong>Patient ID:</strong> {autoResult.patient_id}
                  </p>
                  <p>
                    <strong>Họ tên:</strong> {autoResult.name}
                  </p>
                  <p>
                    <strong>Điện thoại:</strong> {autoResult.phone}
                  </p>
                </>
              ) : null}
            </div>
          ) : null}
        </section>

        <section className="card">
          <h2 className="text-lg font-semibold">2. Tiếp nhận + Routing</h2>
          <ApiCallBadge
            method="POST"
            path={API_ENDPOINTS.reception.intake}
            description="ReceptionDeskPage — intake kèm routing_context.department"
          />

          <form onSubmit={handleIntake} className="space-y-4">
            <div>
              <label className="label-text" htmlFor="department">
                Khoa / Department (điều kiện routing)
              </label>
              <select
                id="department"
                className="input-field"
                value={department}
                onChange={(event) => setDepartment(event.target.value)}
              >
                <option value="emergency">emergency → triage</option>
                <option value="outpatient">outpatient → examination</option>
              </select>
            </div>
            <button type="submit" className="btn-primary" disabled={isLoading}>
              Tiếp nhận &amp; chạy routing
            </button>
          </form>

          {intakeResult ? (
            <div className="mt-4 rounded-lg bg-surface-50 p-4 text-sm">
              <p>
                <strong>Rule:</strong>{" "}
                {intakeResult.routing.rule_name ?? "Không khớp"}
              </p>
              <p>
                <strong>Target stage:</strong>{" "}
                {intakeResult.routing.target_stage ?? "—"}
              </p>
              <p>
                <strong>Matched:</strong>{" "}
                {intakeResult.routing.matched ? "Có" : "Không"}
              </p>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
