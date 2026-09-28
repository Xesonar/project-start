import { apiRequest } from "./client";
import type { ApplicationStatus } from "./applications";
import type { Profile } from "./users";
import type {
  Organization,
  ProjectDetail,
  ProjectDifficulty,
  ProjectFormat,
  ProjectListItem,
  ProjectRole,
  ProjectStatus,
} from "./projects";
import type { SkillLevel } from "./users";
import type { AdminProjectSubmission, SubmissionStatus } from "./submissions";

export interface AdminApplicant {
  id: number;
  name: string;
  avatar_url: string | null;
  is_demo: boolean;
  profile: Profile | null;
}

export interface AdminApplication {
  id: number;
  status: ApplicationStatus;
  message: string | null;
  decision_note: string | null;
  created_at: string;
  project_role: ProjectRole;
  user: AdminApplicant;
}

export interface ProjectCompletionPayload {
  title: string;
  description: string;
  result_url?: string | null;
}

export interface ParticipationConfirmationPayload {
  user_id: number;
}

export interface AdminProjectCreatePayload {
  organization_id: number;
  title: string;
  description: string;
  difficulty: ProjectDifficulty;
  status: Extract<ProjectStatus, "draft" | "open">;
  deadline: string;
  format: ProjectFormat;
  participant_limit: number;
  expected_result: string;
  team_chat_url?: string | null;
  roles: { title: string; description?: string | null; slots: number }[];
  required_skills: { skill_id: number; required_level: SkillLevel }[];
}

export interface AdminMetrics {
  students: number;
  assessed_students: number;
  applications: number;
  accepted_applications: number;
  completed_projects: number;
  confirmed_participations: number;
  assessment_rate: number;
  acceptance_rate: number;
}

export const adminLogin = (password: string) =>
  apiRequest<{ access_token: string }>("/admin/login", {
    method: "POST",
    body: { password },
    auth: false,
  });

export const listAdminProjects = () =>
  apiRequest<ProjectListItem[]>("/admin/projects", { auth: "admin" });

export const getAdminMetrics = () =>
  apiRequest<AdminMetrics>("/admin/metrics", { auth: "admin" });

export const listAdminOrganizations = () =>
  apiRequest<Organization[]>("/admin/organizations", { auth: "admin" });

export const createAdminProject = (payload: AdminProjectCreatePayload) =>
  apiRequest<ProjectDetail>("/admin/projects", {
    method: "POST",
    body: payload,
    auth: "admin",
  });

export const publishAdminProject = (projectId: number) =>
  apiRequest<ProjectListItem>(`/admin/projects/${projectId}/publish`, {
    method: "POST",
    auth: "admin",
  });

export const listProjectApplications = (projectId: number) =>
  apiRequest<AdminApplication[]>(`/admin/projects/${projectId}/applications`, { auth: "admin" });

export const updateApplicationStatus = (
  applicationId: number,
  status: Extract<ApplicationStatus, "accepted" | "rejected">,
  note?: string | null,
) =>
  apiRequest<AdminApplication>(`/admin/applications/${applicationId}`, {
    method: "PATCH",
    body: { status, note },
    auth: "admin",
  });

export const getProjectCommunication = (projectId: number) =>
  apiRequest<{ team_chat_url: string | null }>(
    `/admin/projects/${projectId}/communication`,
    { auth: "admin" },
  );

export const updateProjectCommunication = (projectId: number, teamChatUrl: string | null) =>
  apiRequest<{ team_chat_url: string | null }>(
    `/admin/projects/${projectId}/communication`,
    { method: "PATCH", body: { team_chat_url: teamChatUrl }, auth: "admin" },
  );

export const messageApplicationStudent = (applicationId: number, text: string) =>
  apiRequest<{ delivered: boolean }>(`/admin/applications/${applicationId}/message`, {
    method: "POST",
    body: { text },
    auth: "admin",
  });

export const listProjectSubmissions = (projectId: number) =>
  apiRequest<AdminProjectSubmission[]>(`/admin/projects/${projectId}/submissions`, {
    auth: "admin",
  });

export const reviewProjectSubmission = (
  submissionId: number,
  status: Extract<SubmissionStatus, "approved" | "revision_requested" | "rejected">,
  note?: string | null,
) =>
  apiRequest<AdminProjectSubmission>(`/admin/submissions/${submissionId}`, {
    method: "PATCH",
    body: { status, note },
    auth: "admin",
  });

export const finalizeProject = (
  projectId: number,
  result: ProjectCompletionPayload,
  confirmations: ParticipationConfirmationPayload[],
) =>
  apiRequest<ProjectListItem>(`/admin/projects/${projectId}/finalize`, {
    method: "POST",
    body: { result, confirmations },
    auth: "admin",
  });
