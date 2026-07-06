/** Shared API response and request types. */

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface UserProfile {
  username: string;
  scopes: string[];
}

export interface PatientAutoPopulateResult {
  found: boolean;
  patient_id: number | null;
  name: string | null;
  phone: string | null;
  identity_number: string;
}

export interface RoutingDecision {
  matched: boolean;
  rule_id: number | null;
  rule_name: string | null;
  source_stage: string | null;
  target_stage: string | null;
}

export interface ReceptionIntakeRequest {
  identity_number: string;
  routing_context: {
    source_stage: string;
    patient_id?: number;
    department?: string;
    priority_level?: string;
    metadata?: Record<string, unknown>;
  };
}

export interface ReceptionIntakeResult {
  auto_populate: PatientAutoPopulateResult;
  routing: RoutingDecision;
}

export interface WorkflowListItem {
  id: number;
  patient_id: number;
  patient_name: string;
  current_stage: string;
  status: string;
  assigned_department: string | null;
}

export interface ClinicalRecordRequest {
  record_type: string;
  title: string;
  [key: string]: unknown;
}

export interface ClinicalRecordResponse {
  id: number;
  workflow_id: number;
  patient_id: number;
  author_id: number;
  record_type: string;
  title: string;
  content: string;
  status: string;
  created_at: string;
}

export interface ApiErrorBody {
  detail?: string | { msg: string }[];
}
