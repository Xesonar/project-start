import { useEffect, useState } from "react";

import {
  listProjects,
  type ProjectDifficulty,
  type ProjectFormat,
  type ProjectListItem,
  type ProjectSort,
} from "@/api/projects";
import { ProjectCard } from "@/components/ProjectCard";
import { hapticSelect } from "@/lib/haptics";

const DIFFICULTY_OPTIONS: { value: ProjectDifficulty | "all"; label: string }[] = [
  { value: "all", label: "Любая" },
  { value: "beginner", label: "Начальный" },
  { value: "intermediate", label: "Средний" },
  { value: "advanced", label: "Продвинутый" },
];

const SORT_OPTIONS: { value: ProjectSort; label: string }[] = [
  { value: "newest", label: "Сначала новые" },
  { value: "difficulty", label: "От простых" },
];

const FORMAT_OPTIONS: { value: ProjectFormat | "all"; label: string }[] = [
  { value: "all", label: "Любой формат" },
  { value: "online", label: "Онлайн" },
  { value: "offline", label: "Очно" },
  { value: "hybrid", label: "Гибрид" },
];

export function CatalogScreen() {
  const [projects, setProjects] = useState<ProjectListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [difficulty, setDifficulty] = useState<ProjectDifficulty | "all">("all");
  const [sort, setSort] = useState<ProjectSort>("newest");
  const [format, setFormat] = useState<ProjectFormat | "all">("all");
  const [role, setRole] = useState("");

  const load = () => {
    setError(null);
    setProjects(null);
    listProjects({
      ...(difficulty === "all" ? {} : { difficulty }),
      ...(format === "all" ? {} : { format }),
      ...(role.trim() ? { role: role.trim() } : {}),
      sort,
    })
      .then(setProjects)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Ошибка загрузки"));
  };

  useEffect(load, [difficulty, format, role, sort]);

  return (
    <div className="screen">
      <header>
        <h1 className="screen-title">Найти проект</h1>
        <p className="screen-subtitle">Открытые проекты, которые прямо сейчас набирают команду.</p>
      </header>

      <div className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
        {DIFFICULTY_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            aria-pressed={difficulty === opt.value}
            onClick={() => { hapticSelect(); setDifficulty(opt.value); }}
            className="chip"
          >
            {opt.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-2">
        <select
          value={format}
          onChange={(e) => setFormat(e.target.value as ProjectFormat | "all")}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
          aria-label="Формат проекта"
        >
          {FORMAT_OPTIONS.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
        </select>
        <input
          value={role}
          onChange={(e) => setRole(e.target.value.slice(0, 80))}
          placeholder="Роль, например Frontend"
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
          aria-label="Поиск по роли"
        />
      </div>

      <select
        value={sort}
        onChange={(e) => setSort(e.target.value as ProjectSort)}
        className="min-w-40 self-start rounded-lg border border-slate-200 bg-white py-1.5 pl-3 pr-10 text-sm font-medium text-slate-700 shadow-sm"
      >
        {SORT_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-600">
          <p>{error}</p>
          <button type="button" onClick={load} className="mt-2 font-medium underline">
            Повторить
          </button>
        </div>
      )}

      {!error && projects === null && (
        <div className="flex flex-col gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-24" />
          ))}
        </div>
      )}

      {!error && projects !== null && projects.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-gradient-soft text-3xl">🔍</div>
          <p className="text-sm text-slate-400">
            Проектов по этому фильтру пока нет — попробуй другой уровень сложности.
          </p>
        </div>
      )}

      {!error && projects !== null && projects.length > 0 && (
        <div className="stagger flex flex-col gap-3">
          {projects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}
    </div>
  );
}
