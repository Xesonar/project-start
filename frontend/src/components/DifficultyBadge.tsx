import type { ProjectDifficulty } from "@/api/projects";

const LABELS: Record<ProjectDifficulty, string> = {
  beginner: "Начальный",
  intermediate: "Средний",
  advanced: "Продвинутый",
};

/** dot + label — reads at a glance on a projector, unlike colour alone (a11y) */
const STYLES: Record<ProjectDifficulty, string> = {
  beginner: "bg-emerald-50 text-emerald-700",
  intermediate: "bg-amber-50 text-amber-700",
  advanced: "bg-rose-50 text-rose-700",
};
const DOTS: Record<ProjectDifficulty, string> = {
  beginner: "bg-emerald-500",
  intermediate: "bg-amber-500",
  advanced: "bg-rose-500",
};

export function DifficultyBadge({ difficulty }: { difficulty: ProjectDifficulty }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${STYLES[difficulty]}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${DOTS[difficulty]}`} aria-hidden="true" />
      {LABELS[difficulty]}
    </span>
  );
}
