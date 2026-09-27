import { apiRequest } from "./client";
import type { ProjectListItem } from "./projects";

export interface TeamMember {
  user: { id: number; name: string; avatar_url: string | null };
  role_title: string;
  joined_at: string;
}

export interface Team {
  id: number;
  status: string;
  project: ProjectListItem;
  members: TeamMember[];
  team_chat_url: string | null;
}

export const getMyTeam = () => apiRequest<Team>("/me/team");
