import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  finalizeProject,
  listAdminProjects,
  listProjectApplications,
  updateApplicationStatus,
  type AdminApplication,
} from "@/api/admin";
import type { ProjectListItem } from "@/api/projects";

const STATUS_LABELS: Record<AdminApplication["status"], string> = {
  pending: "На рассмотрении",
  accepted: "Принята",
  rejected: "Отклонена",
  withdrawn: "Отменена студентом",
};

const STATUS_STYLES: Record<AdminApplication["status"], string> = {
  pending: "bg-amber-50 text-amber-700",
  accepted: "bg-emerald-50 text-emerald-700",
  rejected: "bg-slate-100 text-slate-500",
  withdrawn: "bg-slate-100 text-slate-500",
};

export function AdminProjectApplications() {
  const { id } = useParams<{ id: string }>();
  const [applications, setApplications] = useState<AdminApplication[] | null>(null);
  const [project, setProject] = useState<ProjectListItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingActionId, setPendingActionId] = useState<number | null>(null);
  const [resultTitle, setResultTitle] = useState("");
  const [resultDescription, setResultDescription] = useState("");
  const [resultUrl, setResultUrl] = useState("");
  const [contributions, setContributions] = useState<Record<number, string>>({});
  const [finishing, setFinishing] = useState(false);
  const [finishSuccess, setFinishSuccess] = useState(false);

  const load = () => {
    if (!id) return;
    Promise.all([listProjectApplications(Number(id)), listAdminProjects()])
      .then(([nextApplications, projects]) => {
        setApplications(nextApplications);
        setProject(projects.find((item) => item.id === Number(id)) ?? null);
        setContributions((current) => {
          const next = { ...current };
          for (const application of nextApplications) {
            if (application.status === "accepted" && next[application.user.id] === undefined) {
              next[application.user.id] = `Участие в проекте в роли ${application.project_role.title}`;
            }
          }
          return next;
        });
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Ошибка загрузки"));
  };

  const acceptedApplications = Array.from(
    new Map(
      (applications ?? [])
        .filter((application) => application.status === "accepted")
        .map((application) => [application.user.id, application]),
    ).values(),
  );

  const handleFinishProject = async () => {
    if (!id || !resultTitle.trim() || !resultDescription.trim()) return;
    setFinishing(true);
    setFinishSuccess(false);
    setError(null);
    try {
      const completedProject = await finalizeProject(
        Number(id),
        {
          title: resultTitle.trim(),
          description: resultDescription.trim(),
          result_url: resultUrl.trim() || null,
        },
        acceptedApplications.map((application) => ({
          user_id: application.user.id,
          role: application.project_role.title,
          contribution: contributions[application.user.id]?.trim() || null,
        })),
      );
      setProject(completedProject);
      setFinishSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось завершить проект");
    } finally {
      setFinishing(false);
    }
  };

  useEffect(load, [id]);

  const handleDecision = async (applicationId: number, status: "accepted" | "rejected") => {
    setPendingActionId(applicationId);
    try {
      await updateApplicationStatus(applicationId, status);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось обновить статус");
    } finally {
      setPendingActionId(null);
    }
  };

  return (
    <div className="mx-auto flex min-h-full max-w-2xl flex-col gap-4 px-4 py-6">
      <Link to="/admin/projects" className="text-sm text-brand-600">
        ← Ко всем проектам
      </Link>
      <header>
        <h1 className="text-xl font-semibold">{project?.title ?? "Отклики"}</h1>
        {project && <p className="mt-1 text-sm text-slate-500">Управление откликами и результатом проекта</p>}
      </header>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {!error && applications === null && (
        <div className="flex flex-col gap-3">
          {[1, 2].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl bg-slate-100" />
          ))}
        </div>
      )}

      {applications && applications.length === 0 && (
        <p className="py-10 text-center text-sm text-slate-400">Откликов пока нет.</p>
      )}

      {applications && applications.length > 0 && (
        <div className="flex flex-col gap-3">
          {applications.map((app) => (
            <div key={app.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-semibold">{app.user.name}</p>
                  <p className="text-xs text-slate-500">
                    {app.user.profile?.specialty ?? "—"} ·{" "}
                    {app.user.profile?.experience_level ?? "уровень не указан"}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">Роль: {app.project_role.title}</p>
                  {app.message && <p className="mt-1 text-sm text-slate-600">«{app.message}»</p>}
                </div>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[app.status]}`}
                >
                  {STATUS_LABELS[app.status]}
                </span>
              </div>

              {app.status === "pending" && (
                <div className="mt-3 flex gap-2">
                  <button
                    type="button"
                    disabled={pendingActionId === app.id}
                    onClick={() => handleDecision(app.id, "accepted")}
                    className="flex-1 rounded-lg bg-emerald-500 px-3 py-2 text-xs font-medium text-white disabled:opacity-60"
                  >
                    Принять
                  </button>
                  <button
                    type="button"
                    disabled={pendingActionId === app.id}
                    onClick={() => handleDecision(app.id, "rejected")}
                    className="flex-1 rounded-lg bg-slate-200 px-3 py-2 text-xs font-medium text-slate-700 disabled:opacity-60"
                  >
                    Отклонить
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {applications && (
        <section className="mt-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold">Завершение проекта</h2>
              <p className="mt-1 text-xs text-slate-500">
                Результат появится в портфолио всех принятых участников после подтверждения.
              </p>
            </div>
            {project?.status === "completed" && (
              <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700">
                Завершён
              </span>
            )}
          </div>

          {acceptedApplications.length === 0 ? (
            <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-700">
              Сначала примите хотя бы одного участника.
            </p>
          ) : (
            <div className="mt-4 flex flex-col gap-3">
              <label className="text-xs font-medium text-slate-600">
                Название результата
                <input
                  value={resultTitle}
                  onChange={(event) => setResultTitle(event.target.value)}
                  placeholder="Например: Рабочий прототип сервиса"
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal text-slate-900"
                />
              </label>
              <label className="text-xs font-medium text-slate-600">
                Что получилось
                <textarea
                  value={resultDescription}
                  onChange={(event) => setResultDescription(event.target.value)}
                  placeholder="Коротко опишите итог проекта"
                  rows={3}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal text-slate-900"
                />
              </label>
              <label className="text-xs font-medium text-slate-600">
                Ссылка на результат (необязательно)
                <input
                  type="url"
                  value={resultUrl}
                  onChange={(event) => setResultUrl(event.target.value)}
                  placeholder="https://..."
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal text-slate-900"
                />
              </label>

              <div className="border-t border-slate-100 pt-3">
                <p className="mb-2 text-xs font-semibold text-slate-700">Вклад участников</p>
                <div className="flex flex-col gap-2">
                  {acceptedApplications.map((application) => (
                    <label key={application.user.id} className="text-xs text-slate-600">
                      {application.user.name} · {application.project_role.title}
                      <input
                        value={contributions[application.user.id] ?? ""}
                        onChange={(event) =>
                          setContributions((current) => ({
                            ...current,
                            [application.user.id]: event.target.value,
                          }))
                        }
                        className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900"
                      />
                    </label>
                  ))}
                </div>
              </div>

              <button
                type="button"
                onClick={handleFinishProject}
                disabled={finishing || !resultTitle.trim() || !resultDescription.trim()}
                className="btn-primary mt-1 disabled:opacity-50"
              >
                {finishing ? "Сохраняем…" : "Завершить и подтвердить участников"}
              </button>
              {finishSuccess && (
                <p className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700">
                  Проект завершён, участие подтверждено — результат появился в портфолио.
                </p>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
