import { apiRequest } from "./client";
import type { ProjectListItem } from "./projects";

export interface ProjectResult {
  title: string;
  description: string;
  result_url: string | null;
  completed_at: string;
}

export interface Confirmation {
  role: string;
  contribution: string | null;
  confirmed_by: string;
  confirmed_at: string;
}

export interface PortfolioItem {
  project: ProjectListItem;
  result: ProjectResult | null;
  confirmation: Confirmation;
}

export interface PublicSkill {
  name: string;
  category: string;
  level: string;
}

export interface PublicProject {
  project_title: string;
  organization: string;
  role: string;
  contribution: string | null;
  result: ProjectResult | null;
  confirmed_at: string;
}

export interface PublicPortfolio {
  name: string;
  avatar_url: string | null;
  specialty: string | null;
  experience_level: string | null;
  preferred_role: string | null;
  skills: PublicSkill[];
  projects: PublicProject[];
}

export const getMyPortfolio = () => apiRequest<PortfolioItem[]>("/me/portfolio");

export const createPortfolioLink = () =>
  apiRequest<{ slug: string }>("/me/portfolio/link", { method: "POST" });

export const getPortfolioLink = () =>
  apiRequest<{ slug: string | null }>("/me/portfolio/link");

export const regeneratePortfolioLink = () =>
  apiRequest<{ slug: string }>("/me/portfolio/link", { method: "PUT" });

export const revokePortfolioLink = () =>
  apiRequest<void>("/me/portfolio/link", { method: "DELETE" });

/** Public — no token, this is the link a student sends to a recruiter. */
export const getPublicPortfolio = (slug: string) =>
  apiRequest<PublicPortfolio>(`/p/${slug}`, { auth: false });
