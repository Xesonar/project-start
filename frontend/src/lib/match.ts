/** Skill-match math shared by the match ring and any future surface.

Levels are ordered, so "has the skill but below the required level" is worth
something (0.5) rather than nothing — that is the difference between
"нужный навык: SQL" and "придётся подучить SQL", which is the whole point of
the feature for a student with no experience.
*/

import type { ProjectRequiredSkill } from "@/api/projects";
import type { UserSkill } from "@/api/users";

export const LEVEL_ORDER: Record<string, number> = {
  beginner: 0,
  intermediate: 1,
  advanced: 2,
};

export const LEVEL_LABELS: Record<string, string> = {
  beginner: "начальный",
  intermediate: "средний",
  advanced: "продвинутый",
};

export type GapStatus = "missing" | "level";

export interface SkillGap {
  name: string;
  required_level: string;
  status: GapStatus;
}

export interface MatchResult {
  /** 0..1 — share of required skills the student already covers. */
  score: number;
  covered: number;
  total: number;
  gaps: SkillGap[];
}

export function computeMatch(
  required: ProjectRequiredSkill[],
  userSkills: UserSkill[],
): MatchResult {
  const userLevelBySkillId = new Map<number, number>();
  for (const { skill, level, rating } of userSkills) {
    userLevelBySkillId.set(skill.id, rating ?? ((LEVEL_ORDER[level] ?? 0) + 2));
  }

  let weight = 0;
  const gaps: SkillGap[] = [];

  for (const { skill, required_level } of required) {
    const userRating = userLevelBySkillId.get(skill.id);
    if (userRating === undefined) {
      gaps.push({ name: skill.name, required_level, status: "missing" });
      continue;
    }
    const requiredRating = { beginner: 2, intermediate: 3, advanced: 4 }[required_level] ?? 2;
    if (userRating >= requiredRating) {
      weight += 1;
      continue;
    }
    // Knows the skill, but below the bar — half credit, still a gap to show.
    weight += Math.min(userRating / requiredRating, 1);
    gaps.push({ name: skill.name, required_level, status: "level" });
  }

  const total = required.length;
  return {
    score: total === 0 ? 1 : weight / total,
    covered: total - gaps.length,
    total,
    gaps,
  };
}

const VERDICTS: { threshold: number; title: string; hint: string }[] = [
  { threshold: 1.0, title: "Идеальное совпадение", hint: "Закрывай все гэпы на ходу — ты готов(а)" },
  { threshold: 0.7, title: "Сильное совпадение", hint: "Почти всё уже есть, остальное доберёшь в деле" },
  { threshold: 0.4, title: "Чуть-чуть не хватает", hint: "Тянуться вверх полезно — это твой проект роста" },
  { threshold: 0.0, title: "Пока сложноват", hint: "Зато есть понятный план: чему научиться" },
];

export function verdictFor(score: number) {
  return VERDICTS.find((v) => score >= v.threshold) ?? VERDICTS[VERDICTS.length - 1];
}
