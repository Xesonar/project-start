import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  finalizeProject,
  getProjectCommunication,
  listAdminProjects,
  listProjectApplications,
  listProjectSubmissions,
  messageApplicationStudent,
  reviewProjectSubmission,
  updateProjectCommunication,
  updateApplicationStatus,
  type AdminApplication,
} from "@/api/admin";
import type { ProjectListItem } from "@/api/projects";
import type { AdminProjectSubmission } from "@/api/submissions";

const STATUS_LABELS: Record<AdminApplication["status"], string> = {
  pending: "На рассмотрении",
  accepted: "Принята",
  rejected: "Отклонена",
  withdrawn: "Отменена студентом",
  leave_requested: "Запрос выхода",
};

const STATUS_STYLES: Record<AdminApplication["status"], string> = {
  pending: "bg-amber-50 text-amber-700",
  accepted: "bg-emerald-50 text-emerald-700",
  rejected: "bg-slate-100 text-slate-500",
  withdrawn: "bg-slate-100 text-slate-500",
  leave_requested: "bg-violet-50 text-violet-700",
};

const SUBMISSION_STATUS_LABELS: Record<AdminProjectSubmission["status"], string> = {
  submitted: "На проверке",
  revision_requested: "Возвращена на доработку",
  approved: "Подтверждена",
  rejected: "Не подтверждена",
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
  const [finishing, setFinishing] = useState(false);
  const [finishSuccess, setFinishSuccess] = useState(false);
  const [teamChatUrl, setTeamChatUrl] = useState("");
  const [savingChat, setSavingChat] = useState(false);
  const [chatSaved, setChatSaved] = useState(false);
  const [rejectionDrafts, setRejectionDrafts] = useState<Record<number, string>>({});
  const [messageDrafts, setMessageDrafts] = useState<Record<number, string>>({});
  const [sendingMessageId, setSendingMessageId] = useState<number | null>(null);
  const [messageStatuses, setMessageStatuses] = useState<Record<number, string>>({});
  const [submissions, setSubmissions] = useState<AdminProjectSubmission[]>([]);
  const [reviewDrafts, setReviewDrafts] = useState<Record<number, string>>({});
  const [reviewingSubmissionId, setReviewingSubmissionId] = useState<number | null>(null);

  const load = () => {
    if (!id) return;
    Promise.all([
      listProjectApplications(Number(id)),
      listAdminProjects(),
      getProjectCommunication(Number(id)),
      listProjectSubmissions(Number(id)),
    ])
      .then(([nextApplications, projects, communication, nextSubmissions]) => {
        setApplications(nextApplications);
        setProject(projects.find((item) => item.id === Number(id)) ?? null);
        setTeamChatUrl(communication.team_chat_url ?? "");
        setSubmissions(nextSubmissions);
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
  const hasPendingLeaveRequest = (applications ?? []).some(
    (application) => application.status === "leave_requested",
  );
  const submissionsByUser = new Map(submissions.map((submission) => [submission.user_id, submission]));
  const allAcceptedWorkApproved =
    acceptedApplications.length > 0 &&
    acceptedApplications.every(
      (application) => submissionsByUser.get(application.user.id)?.status === "approved",
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

  const handleDecision = async (
    applicationId: number,
    status: "accepted" | "rejected",
    note?: string | null,
  ) => {
    setPendingActionId(applicationId);
    try {
      await updateApplicationStatus(applicationId, status, note);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось обновить статус");
    } finally {
      setPendingActionId(null);
    }
  };

  const handleSaveChat = async () => {
    if (!id) return;
    setSavingChat(true);
    setChatSaved(false);
    setError(null);
    try {
      const result = await updateProjectCommunication(
        Number(id),
        teamChatUrl.trim() || null,
      );
      setTeamChatUrl(result.team_chat_url ?? "");
      setChatSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить ссылку на чат");
    } finally {
      setSavingChat(false);
    }
  };

  const handleMessageStudent = async (applicationId: number) => {
    const text = messageDrafts[applicationId]?.trim();
    if (!text) return;
    setSendingMessageId(applicationId);
    setMessageStatuses((current) => ({ ...current, [applicationId]: "" }));
    try {
      const result = await messageApplicationStudent(applicationId, text);
      setMessageStatuses((current) => ({
        ...current,
        [applicationId]: result.delivered
          ? "Сообщение отправлено в MAX"
          : "MAX не подтвердил доставку. Проверь токен и запуск бота студентом.",
      }));
      if (result.delivered) {
        setMessageDrafts((current) => ({ ...current, [applicationId]: "" }));
      }
    } catch (err) {
      setMessageStatuses((current) => ({
        ...current,
        [applicationId]: err instanceof Error ? err.message : "Не удалось отправить сообщение",
      }));
    } finally {
      setSendingMessageId(null);
    }
  };

  const handleReviewSubmission = async (
    submission: AdminProjectSubmission,
    status: "approved" | "revision_requested" | "rejected",
  ) => {
    const note = reviewDrafts[submission.id]?.trim() || null;
    if (status !== "approved" && !note) return;
    setReviewingSubmissionId(submission.id);
    setError(null);
    try {
      await reviewProjectSubmission(submission.id, status, note);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось проверить результат");
    } finally {
      setReviewingSubmissionId(null);
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

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold">Чат команды в MAX</h2>
        <p className="mt-1 text-xs text-slate-500">
          Принятые студенты получат эту ссылку через бота и увидят её на экране команды.
        </p>
        <div className="mt-3 flex gap-2">
          <input
            type="url"
            value={teamChatUrl}
            onChange={(event) => { setTeamChatUrl(event.target.value); setChatSaved(false); }}
            placeholder="https://max.ru/..."
            className="admin-input min-w-0 flex-1"
          />
          <button
            type="button"
            disabled={savingChat}
            onClick={() => void handleSaveChat()}
            className="rounded-lg bg-brand-600 px-4 text-sm font-medium text-white disabled:opacity-50"
          >
            {savingChat ? "Сохраняем…" : "Сохранить"}
          </button>
        </div>
        {chatSaved && <p className="mt-2 text-xs text-emerald-600">Ссылка сохранена</p>}
      </section>

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
                  {app.user.is_demo && (
                    <p className="mt-0.5 text-xs font-medium text-violet-600">
                      Демо-пользователь — сообщений в MAX нет
                    </p>
                  )}
                  <p className="text-xs text-slate-500">
                    {app.user.profile?.specialty ?? "—"} ·{" "}
                    {app.user.profile?.experience_level ?? "уровень не указан"}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">Роль: {app.project_role.title}</p>
                  {app.message && <p className="mt-1 text-sm text-slate-600">«{app.message}»</p>}
                  {app.decision_note && (
                    <p className="mt-1 text-xs text-slate-500">Комментарий: {app.decision_note}</p>
                  )}
                </div>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[app.status]}`}
                >
                  {STATUS_LABELS[app.status]}
                </span>
              </div>

              {app.status === "pending" && (
                <div className="mt-3 flex flex-col gap-2">
                  <textarea
                    disabled={app.user.is_demo}
                    value={rejectionDrafts[app.id] ?? ""}
                    onChange={(event) =>
                      setRejectionDrafts((current) => ({
                        ...current,
                        [app.id]: event.target.value.slice(0, 500),
                      }))
                    }
                    rows={2}
                    placeholder="Причина отказа для студента"
                    className="admin-input text-xs"
                  />
                  <div className="flex gap-2">
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
                    disabled={pendingActionId === app.id || !rejectionDrafts[app.id]?.trim()}
                    onClick={() => handleDecision(app.id, "rejected", rejectionDrafts[app.id])}
                    className="flex-1 rounded-lg bg-slate-200 px-3 py-2 text-xs font-medium text-slate-700 disabled:opacity-60"
                  >
                    Отклонить
                  </button>
                  </div>
                </div>
              )}

              {app.status === "leave_requested" && (
                <div className="mt-3 rounded-lg bg-violet-50 p-3">
                  <p className="text-xs text-violet-700">
                    Студент просит выйти из команды. До решения место остаётся занятым.
                  </p>
                  <div className="mt-2 flex gap-2">
                    <button
                      type="button"
                      disabled={pendingActionId === app.id}
                      onClick={() => handleDecision(app.id, "accepted", "Запрос выхода отклонён")}
                      className="flex-1 rounded-lg bg-white px-3 py-2 text-xs font-medium text-slate-700"
                    >
                      Оставить в команде
                    </button>
                    <button
                      type="button"
                      disabled={pendingActionId === app.id}
                      onClick={() => handleDecision(app.id, "rejected", "Выход из команды подтверждён")}
                      className="flex-1 rounded-lg bg-red-600 px-3 py-2 text-xs font-medium text-white"
                    >
                      Подтвердить выход
                    </button>
                  </div>
                </div>
              )}

              {(app.status === "accepted" || app.status === "leave_requested") && (() => {
                const submission = submissionsByUser.get(app.user.id);
                if (!submission) {
                  return (
                    <div className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-500">
                      Студент ещё не отправил личный результат на проверку.
                    </div>
                  );
                }
                return (
                  <div className="mt-3 rounded-lg border border-slate-200 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-semibold">Сдача студента</p>
                      <span className="text-xs text-slate-500">
                        {SUBMISSION_STATUS_LABELS[submission.status]}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-slate-700">{submission.summary}</p>
                    {submission.result_url && (
                      <a
                        href={submission.result_url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-2 inline-block text-xs text-brand-600 underline"
                      >
                        Открыть результат
                      </a>
                    )}
                    {submission.review_note && (
                      <p className="mt-2 text-xs text-slate-500">
                        Комментарий проверки: {submission.review_note}
                      </p>
                    )}
                    {submission.status === "submitted" && (
                      <>
                        <textarea
                          value={reviewDrafts[submission.id] ?? ""}
                          onChange={(event) =>
                            setReviewDrafts((current) => ({
                              ...current,
                              [submission.id]: event.target.value.slice(0, 2000),
                            }))
                          }
                          rows={2}
                          placeholder="Комментарий обязателен для возврата или отказа"
                          className="admin-input mt-3 text-xs"
                        />
                        <div className="mt-2 grid grid-cols-3 gap-2">
                          <button
                            type="button"
                            disabled={reviewingSubmissionId === submission.id}
                            onClick={() => void handleReviewSubmission(submission, "approved")}
                            className="rounded-lg bg-emerald-500 px-2 py-2 text-xs font-medium text-white disabled:opacity-50"
                          >
                            Подтвердить
                          </button>
                          <button
                            type="button"
                            disabled={
                              reviewingSubmissionId === submission.id ||
                              !reviewDrafts[submission.id]?.trim()
                            }
                            onClick={() => void handleReviewSubmission(submission, "revision_requested")}
                            className="rounded-lg bg-amber-100 px-2 py-2 text-xs font-medium text-amber-800 disabled:opacity-50"
                          >
                            Доработать
                          </button>
                          <button
                            type="button"
                            disabled={
                              reviewingSubmissionId === submission.id ||
                              !reviewDrafts[submission.id]?.trim()
                            }
                            onClick={() => void handleReviewSubmission(submission, "rejected")}
                            className="rounded-lg bg-red-100 px-2 py-2 text-xs font-medium text-red-700 disabled:opacity-50"
                          >
                            Не подтвердить
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                );
              })()}

              {app.status !== "withdrawn" && (
                <div className="mt-3 border-t border-slate-100 pt-3">
                  <textarea
                    value={messageDrafts[app.id] ?? ""}
                    onChange={(event) =>
                      setMessageDrafts((current) => ({
                        ...current,
                        [app.id]: event.target.value.slice(0, 1000),
                      }))
                    }
                    rows={2}
                    placeholder="Сообщение студенту через бота MAX"
                    className="admin-input text-xs"
                  />
                  <button
                    type="button"
                    disabled={
                      app.user.is_demo ||
                      sendingMessageId === app.id ||
                      !messageDrafts[app.id]?.trim()
                    }
                    onClick={() => void handleMessageStudent(app.id)}
                    className="mt-2 rounded-lg border border-brand-200 px-3 py-2 text-xs font-medium text-brand-700 disabled:opacity-40"
                  >
                    {sendingMessageId === app.id ? "Отправляем…" : "Написать через MAX"}
                  </button>
                  {messageStatuses[app.id] && (
                    <p className="mt-2 text-xs text-slate-500">{messageStatuses[app.id]}</p>
                  )}
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
              {hasPendingLeaveRequest && (
                <p className="rounded-lg bg-violet-50 p-3 text-sm text-violet-700">
                  Сначала обработайте все запросы на выход из команды.
                </p>
              )}
              {!allAcceptedWorkApproved && (
                <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-700">
                  Завершение станет доступно, когда каждый участник отправит результат и организатор его подтвердит.
                </p>
              )}
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
                <p className="mb-2 text-xs font-semibold text-slate-700">Подтверждённый вклад участников</p>
                <div className="flex flex-col gap-2">
                  {acceptedApplications.map((application) => (
                    <div key={application.user.id} className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
                      <p className="font-medium text-slate-800">
                        {application.user.name} · {application.project_role.title}
                      </p>
                      <p className="mt-1">
                        {submissionsByUser.get(application.user.id)?.summary ?? "Результат ещё не подтверждён"}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              <button
                type="button"
                onClick={handleFinishProject}
                disabled={
                  finishing ||
                  hasPendingLeaveRequest ||
                  !allAcceptedWorkApproved ||
                  project?.status === "completed" ||
                  !resultTitle.trim() ||
                  !resultDescription.trim()
                }
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
