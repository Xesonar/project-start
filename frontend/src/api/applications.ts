import { apiRequest } from "./client";
import type { ProjectListItem, ProjectRole } from "./projects";

export type ApplicationStatus = "pending" | "accepted" | "rejected" | "withdrawn";

export interface Application {
  id: number;
  status: ApplicationStatus;
  message: string | null;
  created_at: string;
  project: ProjectListItem;
  project_role: ProjectRole;
}

export const createApplication = (
  projectId: number,
  payload: { project_role_id: number; message?: string | null },
) => apiRequest<Application>(`/projects/${projectId}/applications`, { method: "POST", body: payload });

export const getMyApplications = () => apiRequest<Application[]>("/me/applications");

export const withdrawApplication = (applicationId: number) =>
  apiRequest<void>(`/me/applications/${applicationId}`, { method: "DELETE" });
