import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getAdminMetrics, type AdminMetrics as Metrics } from "@/api/admin";

const CARDS: { key: keyof Metrics; label: string }[] = [
  { key: "students", label: "Студентов" },
  { key: "assessed_students", label: "Прошли диагностику" },
  { key: "applications", label: "Откликов" },
  { key: "accepted_applications", label: "Принято" },
  { key: "completed_projects", label: "Проектов завершено" },
  { key: "confirmed_participations", label: "Подтверждений в портфолио" },
];

export function AdminMetricsScreen() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminMetrics().then(setMetrics).catch((err: unknown) => {
      setError(err instanceof Error ? err.message : "Не удалось загрузить аналитику");
    });
  }, []);

  return (
    <div className="mx-auto flex min-h-full max-w-2xl flex-col gap-5 px-4 py-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Воронка пилота</h1>
          <p className="mt-1 text-sm text-slate-500">Актуальные показатели платформы.</p>
        </div>
        <Link to="/admin/projects" className="text-sm font-medium text-brand-600">Проекты →</Link>
      </header>

      {error ? <p className="rounded-lg bg-danger-50 p-3 text-sm text-danger-700">{error}</p> : null}
      {!metrics && !error ? <div className="skeleton h-52" /> : null}
      {metrics ? (
        <>
          <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/50">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="font-semibold text-amber-900 dark:text-amber-200">Требует внимания</h2>
                <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">
                  Сначала разберите просроченные отклики и работы на проверке.
                </p>
              </div>
              <Link to="/admin/projects" className="shrink-0 text-xs font-semibold text-brand-700">
                Открыть проекты →
              </Link>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
              <QueueMetric label="Новые отклики" value={metrics.pending_applications} />
              <QueueMetric label="Старше 48 часов" value={metrics.overdue_applications} urgent />
              <QueueMetric label="Работы на проверке" value={metrics.pending_submissions} />
              <QueueMetric label="Запросы на выход" value={metrics.leave_requests} urgent />
            </div>
          </section>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {CARDS.map(({ key, label }) => (
              <div key={key} className="card">
                <p className="text-2xl font-bold text-brand-600">{metrics[key]}</p>
                <p className="mt-1 text-xs text-slate-500">{label}</p>
              </div>
            ))}
          </div>
          <section className="card">
            <h2 className="font-semibold">Конверсии</h2>
            <MetricBar label="Диагностика" value={metrics.assessment_rate} />
            <MetricBar label="Принятие откликов" value={metrics.acceptance_rate} />
          </section>
        </>
      ) : null}
    </div>
  );
}

function QueueMetric({ label, value, urgent = false }: { label: string; value: number; urgent?: boolean }) {
  return (
    <div className="rounded-lg bg-white/80 p-3 dark:bg-slate-900/80">
      <p className={`text-xl font-bold ${urgent && value > 0 ? "text-red-600" : "text-slate-900"}`}>
        {value}
      </p>
      <p className="mt-0.5 text-[11px] leading-tight text-slate-500">{label}</p>
    </div>
  );
}

function MetricBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="mt-4">
      <div className="flex justify-between text-sm"><span>{label}</span><strong>{value}%</strong></div>
      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-brand-gradient" style={{ width: `${Math.min(100, value)}%` }} />
      </div>
    </div>
  );
}
