import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listAdminProjects, publishAdminProject } from "@/api/admin";
import { DifficultyBadge } from "@/components/DifficultyBadge";
import type { ProjectListItem } from "@/api/projects";

const STATUS_LABELS: Record<ProjectListItem["status"], string> = {
  draft: "Черновик",
  open: "Открыт",
  in_progress: "В работе",
  completed: "Завершён",
};

export function AdminProjectList() {
  const [projects, setProjects] = useState<ProjectListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [publishingId, setPublishingId] = useState<number | null>(null);

  const publish = async (projectId: number) => {
    setPublishingId(projectId);
    setError(null);
    try {
      const updated = await publishAdminProject(projectId);
      setProjects((current) =>
        current?.map((project) => (project.id === projectId ? updated : project)) ?? null,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось опубликовать проект");
    } finally {
      setPublishingId(null);
    }
  };

  useEffect(() => {
    listAdminProjects()
      .then(setProjects)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Ошибка загрузки"));
  }, []);

  return (
    <div className="mx-auto flex min-h-full max-w-2xl flex-col gap-4 px-4 py-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Проекты</h1>
          <p className="mt-1 text-sm text-slate-500">Выбери проект, чтобы посмотреть отклики.</p>
        </div>
        <Link to="/admin/projects/new" className="btn-primary shrink-0 px-3 py-2 text-sm">
          + Добавить
        </Link>
      </header>
      <Link to="/admin/metrics" className="text-sm font-medium text-brand-600">← Аналитика пилота</Link>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {!error && projects === null && (
        <div className="flex flex-col gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-xl bg-slate-100" />
          ))}
        </div>
      )}

      {projects && (
        <div className="flex flex-col gap-2">
          {projects.map((project) => (
            <div
              key={project.id}
              className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:border-brand-300"
            >
              <Link to={`/admin/projects/${project.id}`} className="min-w-0 flex-1">
                <p className="text-xs text-slate-400">{project.organization.name}</p>
                <p className="truncate text-sm font-medium">{project.title}</p>
              </Link>
              <div className="flex items-center gap-2">
                <DifficultyBadge difficulty={project.difficulty} />
                <span className="text-xs text-slate-500">{STATUS_LABELS[project.status]}</span>
                {project.status === "draft" && (
                  <button
                    type="button"
                    disabled={publishingId === project.id}
                    onClick={() => void publish(project.id)}
                    className="rounded-lg bg-brand-600 px-2.5 py-1.5 text-xs font-medium text-white disabled:opacity-50"
                  >
                    {publishingId === project.id ? "Публикуем…" : "Опубликовать"}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
