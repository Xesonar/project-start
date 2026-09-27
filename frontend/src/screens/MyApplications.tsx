import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  getMyApplications,
  withdrawApplication,
  type Application,
  type ApplicationStatus,
} from "@/api/applications";
import { markApplicationsSeen } from "@/features/notifications";

const STATUS_LABELS: Record<ApplicationStatus, string> = {
  pending: "На рассмотрении",
  accepted: "Принята",
  rejected: "Отклонена",
  withdrawn: "Отменена",
};

const STATUS_STYLES: Record<ApplicationStatus, string> = {
  pending: "bg-amber-50 text-amber-700",
  accepted: "bg-emerald-50 text-emerald-700",
  rejected: "bg-slate-100 text-slate-500",
  withdrawn: "bg-slate-100 text-slate-500",
};

export function MyApplicationsScreen() {
  const [applications, setApplications] = useState<Application[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [withdrawingId, setWithdrawingId] = useState<number | null>(null);

  const load = () => {
    setError(null);
    setApplications(null);
    getMyApplications()
      .then((data) => {
        setApplications(data);
        markApplicationsSeen(data);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Ошибка загрузки"));
  };

  useEffect(() => {
    load();
  }, []);

  const handleWithdraw = async (application: Application) => {
    if (!window.confirm(`Отменить отклик на «${application.project.title}»?`)) return;
    setWithdrawingId(application.id);
    setError(null);
    try {
      await withdrawApplication(application.id);
      setApplications((current) =>
        current?.map((item) =>
          item.id === application.id ? { ...item, status: "withdrawn" } : item,
        ) ?? null,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось отменить отклик");
    } finally {
      setWithdrawingId(null);
    }
  };

  return (
    <div className="screen">
      <header>
        <h1 className="screen-title">Отклики</h1>
        <p className="screen-subtitle">Куда ты отправил заявку и что ответили.</p>
      </header>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-600">
          <p>{error}</p>
          <button type="button" onClick={load} className="mt-2 font-medium underline">Повторить</button>
        </div>
      )}

      {!error && applications === null && (
        <div className="flex flex-col gap-3">
          {[1, 2].map((i) => (
            <div key={i} className="skeleton h-20" />
          ))}
        </div>
      )}

      {!error && applications !== null && applications.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-gradient-soft text-3xl">📭</div>
          <p className="text-sm text-slate-400">Пока нет откликов — найди проект на вкладке «Поиск».</p>
        </div>
      )}

      {!error && applications !== null && applications.length > 0 && (
        <div className="flex flex-col gap-3">
          {applications.map((app) => (
            <div
              key={app.id}
              className="card transition hover:shadow-lift"
            >
              <Link to={`/projects/${app.project.id}`} className="block">
                <p className="text-xs text-slate-400">{app.project.organization.name}</p>
                <h3 className="mt-1 text-sm font-semibold text-slate-900">{app.project.title}</h3>
                <p className="mt-1 text-xs text-slate-500">Роль: {app.project_role.title}</p>
                <span
                  className={`mt-2 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[app.status]}`}
                >
                  {STATUS_LABELS[app.status]}
                </span>
              </Link>
              {app.status === "pending" && (
                <button
                  type="button"
                  disabled={withdrawingId === app.id}
                  onClick={() => void handleWithdraw(app)}
                  className="mt-3 text-xs font-medium text-red-600 underline disabled:opacity-50"
                >
                  {withdrawingId === app.id ? "Отменяем…" : "Отменить отклик"}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
