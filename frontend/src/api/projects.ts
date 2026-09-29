import { apiRequest } from "./client";
import type { Skill, SkillLevel } from "./users";

export type ProjectDifficulty = "beginner" | "intermediate" | "advanced";
export type ProjectStatus =
  | "draft"
  | "open"
  | "recruitment_closed"
  | "in_progress"
  | "completed";
export type ProjectFormat = "online" | "offline" | "hybrid";

export interface Organization {
  id: number;
  name: string;
  description: string;
  type: string;
  verified: boolean;
}

export interface ProjectListItem {
  id: number;
  title: string;
  description: string;
  difficulty: ProjectDifficulty;
  status: ProjectStatus;
  format: ProjectFormat;
  deadline: string;
  participant_limit: number;
  organization: Organization;
}

export interface ProjectRole {
  id: number;
  title: string;
  description: string | null;
  slots: number;
}

export interface ProjectRequiredSkill {
  skill: Skill;
  required_level: SkillLevel;
}

export interface ProjectDetail extends ProjectListItem {
  expected_result: string;
  roles: ProjectRole[];
  required_skills: ProjectRequiredSkill[];
}

export interface ProjectRecommendation extends ProjectListItem {
  score: number;
  breakdown: {
    skills: number;
    role: number;
    specialty: number;
    difficulty: number;
  };
  reason: string | null;
}

export type ProjectSort = "newest" | "difficulty";

export interface ProjectFilters {
  difficulty?: ProjectDifficulty;
  format?: ProjectFormat;
  skill_id?: number[];
  role?: string;
  sort?: ProjectSort;
}

function toQueryString(filters: ProjectFilters): string {
  const params = new URLSearchParams();
  if (filters.difficulty) params.set("difficulty", filters.difficulty);
  if (filters.format) params.set("format", filters.format);
  if (filters.role) params.set("role", filters.role);
  if (filters.sort) params.set("sort", filters.sort);
  for (const id of filters.skill_id ?? []) params.append("skill_id", String(id));
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export const listProjects = (filters: ProjectFilters = {}) =>
  apiRequest<ProjectListItem[]>(`/projects${toQueryString(filters)}`, { auth: false });

export const getProject = (id: number) =>
  apiRequest<ProjectDetail>(`/projects/${id}`, { auth: false });

export const listRecommendedProjects = () =>
  apiRequest<ProjectRecommendation[]>("/projects/recommended");

export const getProjectRecommendation = (id: number) =>
  apiRequest<ProjectRecommendation>(`/projects/${id}/recommendation`);
