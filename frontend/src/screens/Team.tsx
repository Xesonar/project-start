import { useEffect, useState } from "react";

import { ApiError } from "@/api/client";
import { getMyTeams, type Team } from "@/api/team";
import {
  getMyProjectSubmission,
  submitProjectResult,
  type ProjectSubmission,
} from "@/api/submissions";
import { getMaxWebApp } from "@/max/webapp";
import { Link } from "react-router-dom";

const SUBMISSION_LABELS: Record<ProjectSubmission["status"], string> = {
  submitted: "На проверке",
  revision_requested: "Нужна доработка",
  approved: "Подтверждено",
  rejected: "Не подтверждено",
};

function openTeamChat(url: string) {
  const webApp = getMaxWebApp();
  if (webApp) {
    webApp.openMaxLink(url);
  } else {
    window.open(url, "_blank", "noopener,noreferrer");
  }
}

export function TeamScreen() {
  const [teams, setTeams] = useState<Team[] | null>(null);
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null);
  const [notInTeam, setNotInTeam] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submission, setSubmission] = useState<ProjectSubmission | null>(null);
  const [summary, setSummary] = useState("");
  const [resultUrl, setResultUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const team = teams?.find((item) => item.id === selectedTeamId) ?? null;

  const load = () => {
    setError(null);
    setNotInTeam(false);
    setTeams(null);
    getMyTeams()
      .then((nextTeams) => {
        setTeams(nextTeams);
        setNotInTeam(nextTeams.length === 0);
        setSelectedTeamId((current) =>
          current && nextTeams.some((item) => item.id === current)
            ? current
            : (nextTeams[0]?.id ?? null),
        );
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Ошибка загрузки");
      });
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!team) {
      setSubmission(null);
      setSummary("");
      setResultUrl("");
      return;
    }
    let cancelled = false;
    setSubmission(null);
    setSummary("");
    setResultUrl("");
    getMyProjectSubmission(team.project.id)
      .then((nextSubmission) => {
        if (cancelled) return;
        setSubmission(nextSubmission);
        setSummary(nextSubmission.summary);
        setResultUrl(nextSubmission.result_url ?? "");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) return;
        setError(err instanceof Error ? err.message : "Ошибка загрузки результата");
      });
    return () => {
      cancelled = true;
    };
  }, [team?.id, team?.project.id]);

  const handleSubmit = async () => {
    if (!team || summary.trim().length < 10) return;
    setSubmitting(true);
    setError(null);
    try {
      const nextSubmission = await submitProjectResult(team.project.id, {
        summary: summary.trim(),
        result_url: resultUrl.trim() || null,
      });
      setSubmission(nextSubmission);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось отправить результат");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="screen">
      <header>
        <h1 className="screen-title">Моя команда</h1>
        <p className="screen-subtitle">Все проекты, в которых ты участвуешь.</p>
      </header>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-600">
          <p>{error}</p>
          <button type="button" onClick={load} className="mt-2 font-medium underline">Повторить</button>
        </div>
      )}

      {notInTeam && (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-gradient-soft text-3xl">🧑‍🤝‍🧑</div>
          <p className="text-sm text-slate-400">Пока ты не в команде — дождись решения по своим откликам.</p>
        </div>
      )}

      {!error && !notInTeam && teams === null && (
        <div className="skeleton h-32" />
      )}

      {team && (
        <>
          {teams && teams.length > 1 && (
            <div className="no-scrollbar flex gap-2 overflow-x-auto pb-1">
              {teams.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  aria-pressed={item.id === team.id}
                  onClick={() => setSelectedTeamId(item.id)}
                  className="chip max-w-56 truncate"
                >
                  {item.project.title}
                </button>
              ))}
            </div>
          )}
          <div className="card">
            <p className="text-xs text-slate-400">{team.project.organization.name}</p>
            <h2 className="mt-1 text-sm font-semibold">{team.project.title}</h2>
            {team.status === "completed" && (
              <p className="mt-2 text-xs font-medium text-emerald-600">
                Проект завершён, подтверждённый результат сохранён в портфолио.
              </p>
            )}
          </div>

          <div className="stagger flex flex-col gap-2">
            {team.members.map((member) => (
              <div
                key={member.user.id}
                className="flex items-center justify-between rounded-lg border border-slate-200 p-3"
              >
                <span className="text-sm font-medium">{member.user.name}</span>
                <span className="text-xs text-slate-500">{member.role_title}</span>
              </div>
            ))}
          </div>

          {team.team_chat_url && (
            <button
              type="button"
              onClick={() => openTeamChat(team.team_chat_url!)}
              className="btn-primary"
            >
              Открыть чат команды
            </button>
          )}

          {team.status === "completed" ? (
            <Link to="/portfolio" className="btn-primary text-center">
              Открыть портфолио
            </Link>
          ) : (
            <section className="card">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-sm font-semibold">Сдать личный результат</h2>
                  <p className="mt-1 text-xs text-slate-500">
                    Опиши свой вклад. После проверки именно этот текст попадёт в портфолио.
                  </p>
                </div>
                {submission && (
                  <span className="rounded-full bg-brand-50 px-2 py-1 text-xs font-medium text-brand-700">
                    {SUBMISSION_LABELS[submission.status]}
                  </span>
                )}
              </div>
              {submission?.review_note && (
                <p className="mt-3 rounded-lg bg-amber-50 p-3 text-xs text-amber-700">
                  Комментарий организатора: {submission.review_note}
                </p>
              )}
              <label className="mt-3 block text-xs font-medium text-slate-600">
                Что ты сделал
                <textarea
                  value={summary}
                  onChange={(event) => setSummary(event.target.value.slice(0, 3000))}
                  rows={4}
                  placeholder="Например: разработал API, настроил базу данных и написал тесты"
                  className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-normal text-slate-900"
                />
              </label>
              <label className="mt-3 block text-xs font-medium text-slate-600">
                Ссылка на результат (необязательно)
                <input
                  type="url"
                  value={resultUrl}
                  onChange={(event) => setResultUrl(event.target.value)}
                  placeholder="https://github.com/..."
                  className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-normal text-slate-900"
                />
              </label>
              <button
                type="button"
                onClick={() => void handleSubmit()}
                disabled={submitting || summary.trim().length < 10}
                className="btn-primary mt-3 w-full disabled:opacity-50"
              >
                {submitting
                  ? "Отправляем…"
                  : submission
                    ? "Отправить результат повторно"
                    : "Отправить на проверку"}
              </button>
              {submission?.status === "approved" && (
                <p className="mt-2 text-xs text-slate-500">
                  Если изменишь результат, организатор должен будет подтвердить его заново.
                </p>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}
