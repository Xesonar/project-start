import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getMyApplications, type Application, type ApplicationStatus } from "@/api/applications";
import { markApplicationsSeen } from "@/features/notifications";

const STATUS_LABELS: Record<ApplicationStatus, string> = {
  pending: "На рассмотрении",
  accepted: "Принята",
  rejected: "Отклонена",
};

const STATUS_STYLES: Record<ApplicationStatus, string> = {
  pending: "bg-amber-50 text-amber-700",
  accepted: "bg-emerald-50 text-emerald-700",
  rejected: "bg-slate-100 text-slate-500",
};

export function MyApplicationsScreen() {
  const [applications, setApplications] = useState<Application[] | null>(null);
  const [error, setError] = useState<string | null>(null);

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
            <Link
              key={app.id}
              to={`/projects/${app.project.id}`}
              className="card block transition hover:shadow-lift"
            >
              <p className="text-xs text-slate-400">{app.project.organization.name}</p>
              <h3 className="mt-1 text-sm font-semibold text-slate-900">{app.project.title}</h3>
              <p className="mt-1 text-xs text-slate-500">Роль: {app.project_role.title}</p>
              <span
                className={`mt-2 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[app.status]}`}
              >
                {STATUS_LABELS[app.status]}
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
