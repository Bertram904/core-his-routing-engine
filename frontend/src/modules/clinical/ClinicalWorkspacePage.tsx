import { FormEvent, useEffect, useState } from "react";

import { API_ENDPOINTS } from "@/api/endpoints";
import { ApiError } from "@/api/httpClient";
import {
  createClinicalRecordApi,
  exportWorkflowPdfApi,
  listWorkflowsApi,
} from "@/api/clinical.api";
import { useAuth } from "@/auth/AuthContext";
import { ApiCallBadge } from "@/components/ui/ApiCallBadge";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBanner } from "@/components/ui/StatusBanner";
import type {
  ClinicalRecordResponse,
  WorkflowListItem,
} from "@/types/api.types";

export function ClinicalWorkspacePage() {
  const { token } = useAuth();
  const [workflows, setWorkflows] = useState<WorkflowListItem[]>([]);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<number | null>(
    null,
  );
  const [recordType, setRecordType] = useState("examination_note");
  const [title, setTitle] = useState("Kham tong quat");
  const [chiefComplaint, setChiefComplaint] = useState("Dau dau");
  const [diagnosis, setDiagnosis] = useState("Benh nhe");
  const [lastRecord, setLastRecord] = useState<ClinicalRecordResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!token) {
      return;
    }

    listWorkflowsApi(token)
      .then((items) => {
        setWorkflows(items);
        if (items.length > 0) {
          setSelectedWorkflowId(items[0].id);
        }
      })
      .catch((loadError) => {
        setError(
          loadError instanceof ApiError
            ? loadError.message
            : "Không tải được danh sách workflow",
        );
      });
  }, [token]);

  async function handleCreateRecord(event: FormEvent) {
    event.preventDefault();
    if (!token || selectedWorkflowId === null) {
      return;
    }

    setError(null);
    setSuccess(null);
    setIsLoading(true);

    try {
      const record = await createClinicalRecordApi(token, selectedWorkflowId, {
        record_type: recordType,
        title,
        chief_complaint: chiefComplaint,
        diagnosis,
      });
      setLastRecord(record);
      setSuccess(`Đã tạo hồ sơ #${record.id} cho workflow ${selectedWorkflowId}`);
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "Tạo hồ sơ thất bại",
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function handleExportPdf() {
    if (!token || selectedWorkflowId === null) {
      return;
    }

    setError(null);
    setSuccess(null);
    setIsLoading(true);

    try {
      await exportWorkflowPdfApi(token, selectedWorkflowId);
      setSuccess(`Đã tải PDF workflow ${selectedWorkflowId}`);
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "Xuất PDF thất bại",
      );
    } finally {
      setIsLoading(false);
    }
  }

  const selectedWorkflow = workflows.find(
    (workflow) => workflow.id === selectedWorkflowId,
  );

  return (
    <div>
      <PageHeader
        moduleLabel="Clinical · write:clinical_record"
        title="Phòng khám / Lâm sàng"
        subtitle="Tạo hồ sơ JSON động và xuất PDF workflow."
      />

      {error ? (
        <div className="mb-4">
          <StatusBanner type="error" message={error} />
        </div>
      ) : null}
      {success ? (
        <div className="mb-4">
          <StatusBanner type="success" message={success} />
        </div>
      ) : null}

      <section className="card mb-6">
        <h2 className="text-lg font-semibold">Chọn workflow</h2>
        <ApiCallBadge
          method="GET"
          path={API_ENDPOINTS.clinical.workflows}
          description="ClinicalWorkspacePage — load danh sách workflow khi vào màn hình"
        />

        <select
          className="input-field max-w-xl"
          value={selectedWorkflowId ?? ""}
          onChange={(event) =>
            setSelectedWorkflowId(Number(event.target.value))
          }
        >
          {workflows.map((workflow) => (
            <option key={workflow.id} value={workflow.id}>
              #{workflow.id} — {workflow.patient_name} ({workflow.current_stage})
            </option>
          ))}
        </select>

        {selectedWorkflow ? (
          <div className="mt-4 grid gap-2 text-sm text-slate-600 md:grid-cols-3">
            <p>
              <strong>Stage:</strong> {selectedWorkflow.current_stage}
            </p>
            <p>
              <strong>Status:</strong> {selectedWorkflow.status}
            </p>
            <p>
              <strong>Department:</strong>{" "}
              {selectedWorkflow.assigned_department ?? "—"}
            </p>
          </div>
        ) : null}
      </section>

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="card">
          <h2 className="text-lg font-semibold">Tạo hồ sơ lâm sàng</h2>
          <ApiCallBadge
            method="POST"
            path="/api/v1/workflows/{workflow_id}/record"
            description="ClinicalWorkspacePage — JSON động, field thêm ngoài record_type/title"
          />

          <form onSubmit={handleCreateRecord} className="space-y-4">
            <div>
              <label className="label-text" htmlFor="recordType">
                record_type
              </label>
              <input
                id="recordType"
                className="input-field"
                value={recordType}
                onChange={(event) => setRecordType(event.target.value)}
              />
            </div>
            <div>
              <label className="label-text" htmlFor="title">
                title
              </label>
              <input
                id="title"
                className="input-field"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
              />
            </div>
            <div>
              <label className="label-text" htmlFor="complaint">
                chief_complaint (dynamic field)
              </label>
              <input
                id="complaint"
                className="input-field"
                value={chiefComplaint}
                onChange={(event) => setChiefComplaint(event.target.value)}
              />
            </div>
            <div>
              <label className="label-text" htmlFor="diagnosis">
                diagnosis (dynamic field)
              </label>
              <input
                id="diagnosis"
                className="input-field"
                value={diagnosis}
                onChange={(event) => setDiagnosis(event.target.value)}
              />
            </div>
            <button type="submit" className="btn-primary" disabled={isLoading}>
              Lưu hồ sơ
            </button>
          </form>

          {lastRecord ? (
            <pre className="mt-4 overflow-x-auto rounded-lg bg-surface-900 p-4 text-xs text-emerald-200">
              {JSON.stringify(lastRecord, null, 2)}
            </pre>
          ) : null}
        </section>

        <section className="card">
          <h2 className="text-lg font-semibold">Xuất PDF báo cáo</h2>
          <ApiCallBadge
            method="GET"
            path="/api/v1/workflows/{workflow_id}/export-pdf"
            description="ClinicalWorkspacePage — stream PDF qua WeasyPrint backend"
          />
          <p className="mb-4 text-sm text-slate-500">
            PDF gồm thông tin workflow, bệnh nhân và toàn bộ clinical records.
          </p>
          <button
            type="button"
            className="btn-secondary"
            onClick={handleExportPdf}
            disabled={isLoading || selectedWorkflowId === null}
          >
            Tải PDF
          </button>
        </section>
      </div>
    </div>
  );
}
