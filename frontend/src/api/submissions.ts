import { apiRequest } from "./client";

export type SubmissionStatus =
  | "submitted"
  | "revision_requested"
  | "approved"
  | "rejected";

export interface ProjectSubmission {
  id: number;
  project_id: number;
  user_id: number;
  summary: string;
  result_url: string | null;
  status: SubmissionStatus;
  review_note: string | null;
  submitted_at: string;
  reviewed_at: string | null;
}

export interface AdminProjectSubmission extends ProjectSubmission {
  user: { id: number; name: string; avatar_url: string | null };
}

export const getMyProjectSubmission = (projectId: number) =>
  apiRequest<ProjectSubmission>(`/me/projects/${projectId}/submission`);

export const submitProjectResult = (
  projectId: number,
  payload: { summary: string; result_url?: string | null },
) =>
  apiRequest<ProjectSubmission>(`/me/projects/${projectId}/submission`, {
    method: "PUT",
    body: payload,
  });
