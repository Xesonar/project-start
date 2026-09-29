import { Link } from "react-router-dom";

import type { ProjectListItem } from "@/api/projects";
import { DifficultyBadge } from "@/components/DifficultyBadge";
import { hapticSelect } from "@/lib/haptics";

const FORMAT_LABELS: Record<ProjectListItem["format"], string> = {
  online: "Онлайн",
  offline: "Очно",
  hybrid: "Гибрид",
};

export function ProjectCard({ project }: { project: ProjectListItem & { reason?: string | null; score?: number | null } }) {
  return (
    <Link
      to={`/projects/${project.id}`}
      onClick={() => hapticSelect()}
      className="card block transition duration-200 ease-out-expo hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-lift active:scale-[0.985]"
    >
      <div className="flex items-center justify-between gap-2">
        <p className="truncate text-xs font-medium text-slate-400">
          {project.organization.name}
        </p>
        {typeof project.score === "number" && project.score > 0 ? (
          <span
            className="shrink-0 rounded-full bg-brand-gradient px-2 py-0.5 text-[10px] font-bold tabular-nums text-white"
            aria-label={`Общее совпадение профиля ${Math.round(project.score * 100)}%`}
          >
            {Math.round(project.score * 100)}%
          </span>
        ) : null}
        {project.organization.verified ? (
          <span
            title="Организация верифицирована"
            className="flex shrink-0 items-center gap-1 text-[10px] font-semibold text-brand-600"
          >
            <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="m5 12.5 4.5 4.5L19 7.5"
                stroke="currentColor"
                strokeWidth="2.4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            проверено
          </span>
        ) : null}
      </div>

      <h3 className="mt-1.5 text-[15px] font-bold leading-snug text-slate-900">
        {project.title}
      </h3>
      <p className="mt-1 line-clamp-2 text-sm text-slate-500">{project.description}</p>

      <div className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1.5 text-xs text-slate-500">
        <DifficultyBadge difficulty={project.difficulty} />
        <Dot />
        <span>{FORMAT_LABELS[project.format]}</span>
        <Dot />
        <span>{project.deadline}</span>
        <Dot />
        <span className="font-medium">{project.participant_limit} мест</span>
        {project.applicants_count > 0 ? (
          <>
            <Dot />
            <span className="font-medium text-brand-600">
              {project.applicants_count} {project.applicants_count === 1 ? "заявка" : "заявок"}
            </span>
          </>
        ) : null}
      </div>

      {project.reason ? (
        <p className="mt-3 flex gap-1.5 rounded-lg bg-brand-gradient-soft px-2.5 py-1.5 text-xs leading-snug text-brand-700 dark:bg-brand-950/60 dark:text-brand-200">
          <span aria-hidden="true" className="shrink-0">✦</span>
          <span>
            <span className="font-semibold">Почему тебе:</span> {project.reason}
          </span>
        </p>
      ) : null}
    </Link>
  );
}

function Dot() {
  return <span className="text-slate-300" aria-hidden="true">·</span>;
}
