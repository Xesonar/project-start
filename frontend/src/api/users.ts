import { apiRequest } from "./client";

export type ExperienceLevel = "beginner" | "intermediate" | "advanced";
export type SkillLevel = "beginner" | "intermediate" | "advanced";

export interface Profile {
  university: string | null;
  course: number | null;
  specialty: string | null;
  about: string | null;
  experience_level: ExperienceLevel | null;
  portfolio_url: string | null;
  github_url: string | null;
  goal: string | null;
  preferred_role: string | null;
}

export interface Me {
  id: number;
  name: string;
  avatar_url: string | null;
  role: string;
  profile: Profile | null;
  xp: number;
  level: number;
  next_level_xp: number | null;
}

export interface Skill {
  id: number;
  name: string;
  category: string;
}

export interface UserSkill {
    skill: Skill;
    level: SkillLevel;
    rating: number;
}

export const getMe = () => apiRequest<Me>("/me");

export const updateProfile = (payload: Partial<Profile>) =>
  apiRequest<Me>("/me/profile", { method: "PATCH", body: payload });

export const listSkills = () => apiRequest<Skill[]>("/skills", { auth: false });

export const getMySkills = () => apiRequest<UserSkill[]>("/me/skills");

export const setMySkills = (items: { skill_id: number; level: SkillLevel; rating?: number }[]) =>
  apiRequest<UserSkill[]>("/me/skills", { method: "PUT", body: items });

export const saveMyAssessment = (
  profile: Partial<Profile>,
  skills: { skill_id: number; level: SkillLevel; rating?: number }[],
) => apiRequest<Me>("/me/assessment", { method: "PUT", body: { profile, skills } });
