import axios from "axios";

const BASE = process.env.REACT_APP_API_URL || "http://localhost:8080";

export const api = axios.create({
  baseURL: BASE,
  withCredentials: true, // send session cookie
});

export interface WorkflowItem {
  id: string;
  study_id: string;
  workflow_type: string;
  status: "pending_upload" | "pending_followup" | "completed" | "archived";
  role1_data?: {
    patient_last_name: string;
    patient_first_name: string;
    date_of_birth: string;
    mrn: string;
    medicare: boolean;
    clinical_note_expiration?: string;
    comments?: string;
    pdf_gcs_path?: string;
    completed_at?: string;
    completed_by?: string;
  };
  role2_data?: {
    followup_note: string;
    confirmed_at?: string;
    confirmed_by?: string;
  };
  created_at?: string;
  updated_at?: string;
  archived_at?: string;
}

export interface Me {
  email: string;
  role: "uploader" | "reviewer" | "admin";
  name: string;
}

export const getMe = () => api.get<Me>("/auth/me").then((r) => r.data);

export const getUploadQueue = () =>
  api.get<WorkflowItem[]>("/items/upload-queue").then((r) => r.data);

export const getFollowupQueue = () =>
  api.get<WorkflowItem[]>("/items/followup-queue").then((r) => r.data);

export const getItem = (id: string) =>
  api.get<WorkflowItem>(`/items/${id}`).then((r) => r.data);

export const getPdfUrl = (id: string) =>
  api.get<{ url: string }>(`/items/${id}/pdf-url`).then((r) => r.data.url);

export const submitUpload = (id: string, form: FormData) =>
  api.post<WorkflowItem>(`/items/${id}/submit-upload`, form).then((r) => r.data);

export const confirmFollowup = (id: string, followup_note: string) =>
  api
    .post<WorkflowItem>(`/items/${id}/confirm-followup`, { followup_note })
    .then((r) => r.data);

export const getCompleted = () =>
  api.get<WorkflowItem[]>("/archive/completed").then((r) => r.data);

export const getArchived = () =>
  api.get<WorkflowItem[]>("/archive").then((r) => r.data);

export const reactivateItem = (id: string, reason: string) =>
  api.post<WorkflowItem>(`/archive/${id}/reactivate`, { reason }).then((r) => r.data);

export const createItem = (study_id: string) =>
  api.post<WorkflowItem>("/items", { study_id }).then((r) => r.data);

export interface GmailStatus {
  connected: boolean;
  connected_email: string | null;
  connected_at: string | null;
  check_interval_minutes: number;
  lookback_days: number;
  last_checked_at: string | null;
  last_run_status: string | null;
  last_run_summary: string | null;
  last_run_error: string | null;
}

export const getGmailStatus = () =>
  api.get<GmailStatus>("/admin/gmail/status").then((r) => r.data);

export const disconnectGmail = () => api.post("/admin/gmail/disconnect");

export const updateGmailSettings = (check_interval_minutes: number, lookback_days: number) =>
  api
    .put<GmailStatus>("/admin/gmail/settings", { check_interval_minutes, lookback_days })
    .then((r) => r.data);

export const checkGmailNow = () =>
  api
    .post<{ status: string; created?: number; skipped?: number }>("/admin/gmail/check-now")
    .then((r) => r.data);

export const gmailConnectUrl = () => `${BASE}/admin/gmail/connect`;
