import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { createApplication, getMyApplications, type Application } from "@/api/applications";
import {
  getProject,
  getProjectRecommendation,
  type ProjectDetail,
  type ProjectRecommendation,
} from "@/api/projects";
import { getMySkills, type UserSkill } from "@/api/users";
import { DifficultyBadge } from "@/components/DifficultyBadge";
import { MatchRing } from "@/components/MatchRing";
import { computeMatch, type MatchResult } from "@/lib/match";
import { hapticError, hapticSelect, hapticSuccess } from "@/lib/haptics";
import { useMaxBackButton } from "@/max/useMaxBackButton";

const FORMAT_LABELS: Record<ProjectDetail["format"], string> = {
  online: "Онлайн",
  offline: "Очно",
  hybrid: "Гибрид",
};

const SKILL_LEVEL_LABELS: Record<string, string> = {
  beginner: "начальный",
  intermediate: "средний",
  advanced: "продвинутый",
};

const blocksRoleSelection = (application: Application) =>
  application.status === "pending" ||
  application.status === "accepted" ||
  application.status === "leave_requested";

export function ProjectDetailScreen() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  // A project can be opened from a MAX deep link without browser history.
  // Returning home is deterministic; navigate(-1) could close the Mini App.
  const goBack = useCallback(() => navigate("/"), [navigate]);
  useMaxBackButton(goBack);
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [skills, setSkills] = useState<UserSkill[] | null>(null);
  const [applications, setApplications] = useState<Application[] | null>(null);
  const [recommendation, setRecommendation] = useState<ProjectRecommendation | null | undefined>();
  const [error, setError] = useState<string | null>(null);
  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
  const [applyState, setApplyState] = useState<"idle" | "submitting" | "done" | "error">("idle");
  const [applyError, setApplyError] = useState<string | null>(null);
  const [applicationMessage, setApplicationMessage] = useState("");

  const load = useCallback(() => {
    if (!id) return;
    setError(null);
    setProject(null);
    setRecommendation(undefined);
    Promise.all([
      getProject(Number(id)),
      getMyApplications().catch(() => []),
      getProjectRecommendation(Number(id)).catch(() => null),
    ])
      .then(([data, currentApplications, currentRecommendation]) => {
        const appliedRoleIds = new Set(
          currentApplications
            .filter(
              (application) =>
                application.project.id === data.id && blocksRoleSelection(application),
            )
            .map((application) => application.project_role.id),
        );
        setProject(data);
        setApplications(currentApplications);
        setRecommendation(currentRecommendation);
        setSelectedRoleId(
          data.status === "open"
            ? (data.roles.find((role) => !appliedRoleIds.has(role.id))?.id ?? null)
            : null,
        );
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Ошибка загрузки"));
    // Skills load in parallel — the match ring is meaningless without them,
    // but they must never block the project itself from rendering.
    getMySkills().then(setSkills).catch(() => setSkills([]));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const match: MatchResult | null =
    project && skills ? computeMatch(project.required_skills, skills) : null;

  const handleApply = async () => {
    if (!project || selectedRoleId === null) return;
    setApplyState("submitting");
    setApplyError(null);
    hapticSelect();
    try {
      const created = await createApplication(project.id, {
        project_role_id: selectedRoleId,
        message: applicationMessage.trim() || null,
      });
      setApplications((current) => [
        ...(current ?? []).filter(
          (application) =>
            !(
              application.project.id === project.id &&
              application.project_role.id === selectedRoleId
            ),
        ),
        created,
      ]);
      setApplyState("done");
      setApplicationMessage("");
      const appliedRoleId = selectedRoleId;
      const blockedRoleIds = new Set(
        [...(applications ?? []), created]
          .filter(
            (application) =>
              application.project.id === project.id && blocksRoleSelection(application),
          )
          .map((application) => application.project_role.id),
      );
      setSelectedRoleId(
        project.roles.find(
          (role) => role.id !== appliedRoleId && !blockedRoleIds.has(role.id),
        )?.id ?? null,
      );
      setProject((current) => current ? {
        ...current,
        applicants_count: current.applicants_count + 1,
        roles: current.roles.map((role) => role.id === appliedRoleId
          ? { ...role, applicants_count: role.applicants_count + 1 }
          : role),
      } : current);
      hapticSuccess();
    } catch (err) {
      setApplyError(err instanceof Error ? err.message : "Не удалось отправить отклик");
      setApplyState("error");
      hapticError();
    }
  };

  if (error) {
    return (
      <div className="mx-auto max-w-md px-4 py-6 text-sm text-danger-700">
        <p>Не удалось загрузить проект: {error}</p>
        <button type="button" onClick={load} className="mt-2 font-medium underline">
          Повторить
        </button>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="mx-auto flex max-w-md flex-col gap-3 px-4 py-6">
        <div className="skeleton h-6 w-2/3" />
        <MatchRing match={null} loading />
        <div className="skeleton h-24" />
      </div>
    );
  }

  return (
    <div className="screen gap-5">
      <Link to="/" className="-ml-1 inline-flex items-center gap-1 text-sm font-medium text-brand-600">
        <span aria-hidden="true">←</span> Ко всем проектам
      </Link>

      <header>
        <p className="text-xs text-slate-400">{project.organization.name}</p>
        <h1 className="mt-1 text-2xl font-bold leading-tight tracking-tight">{project.title}</h1>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <DifficultyBadge difficulty={project.difficulty} />
          <span>·</span>
          <span>{FORMAT_LABELS[project.format]}</span>
          <span>·</span>
          <span>{project.deadline}</span>
          <span>·</span>
          <span>до {project.participant_limit} мест</span>
        </div>
      </header>

      {/* The magic beat: "насколько это вообще моё" before the student reads
          a wall of text. Lives above the description on purpose. */}
      <MatchRing
        match={match}
        overallScore={recommendation?.score ?? null}
        breakdown={recommendation?.breakdown}
        loading={skills === null || recommendation === undefined}
      />

      <section>
        <h2 className="mb-1 text-sm font-medium text-slate-700">Описание</h2>
        <p className="text-sm text-slate-600">{project.description}</p>
      </section>

      <section>
        <h2 className="mb-1 text-sm font-medium text-slate-700">Ожидаемый результат</h2>
        <p className="text-sm text-slate-600">{project.expected_result}</p>
      </section>

      <section>
        <h2 className="mb-2 text-sm font-medium text-slate-700">Выбери роль</h2>
        {project.status !== "open" && (
          <p className="mb-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-700">
            Набор в этот проект уже закрыт.
          </p>
        )}
        <div className="flex flex-col gap-2">
          {project.roles.map((role) => {
            const existingApplication = applications?.find(
              (application) =>
                application.project.id === project.id &&
                application.project_role.id === role.id &&
                blocksRoleSelection(application),
            );
            return (
            <button
              key={role.id}
              type="button"
              disabled={
                project.status !== "open" ||
                Boolean(existingApplication)
              }
              aria-pressed={selectedRoleId === role.id}
              onClick={() => { hapticSelect(); setSelectedRoleId(role.id); }}
              className={`rounded-lg border p-3 text-left transition active:scale-[0.99] disabled:opacity-60 ${
                selectedRoleId === role.id
                  ? "border-brand-500 bg-brand-50 shadow-soft ring-1 ring-brand-200 dark:border-brand-400 dark:bg-brand-950 dark:ring-brand-800"
                  : "border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900"
              }`}
            >
              <p className="text-sm font-medium">{role.title}</p>
              {role.description && (
                <p className="mt-0.5 text-xs text-slate-500">{role.description}</p>
              )}
              <p className="mt-1 text-xs text-slate-400">мест: {role.slots}</p>
              {role.applicants_count > 0 && (
                <p className="mt-1 text-xs font-medium text-brand-600">
                  {role.applicants_count} {role.applicants_count === 1 ? "заявка" : "заявок"} на роль
                </p>
              )}
              {existingApplication && (
                <p className="mt-1 text-xs font-medium text-brand-600">
                  Отклик уже отправлен
                </p>
              )}
            </button>
            );
          })}
        </div>
      </section>

      <section>
        <h2 className="mb-2 text-sm font-medium text-slate-700">Нужные навыки</h2>
        <div className="flex flex-wrap gap-2">
          {project.required_skills.map(({ skill, required_level }) => (
            <span
              key={skill.id}
              className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 shadow-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
            >
              {skill.name} · {SKILL_LEVEL_LABELS[required_level]}
            </span>
          ))}
        </div>
      </section>

      {project.status !== "open" ? (
        <Link to="/catalog" className="btn-primary mt-2 text-center">
          Найти открытый проект
        </Link>
      ) : selectedRoleId === null && applications !== null ? (
        <Link to="/applications" className="btn-primary mt-2 text-center">
          Посмотреть мои отклики
        </Link>
      ) : (
        <div className="mt-2 flex flex-col gap-3">
          <label className="text-sm font-medium text-slate-700">
            Сообщение организатору <span className="font-normal text-slate-400">необязательно</span>
            <textarea
              value={applicationMessage}
              onChange={(event) => setApplicationMessage(event.target.value.slice(0, 500))}
              rows={3}
              placeholder="Почему тебе интересен проект и чем ты можешь помочь"
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-normal text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
            />
            <span className="mt-1 block text-right text-xs font-normal text-slate-400">
              {applicationMessage.length}/500
            </span>
          </label>
          <button
            type="button"
            onClick={handleApply}
            disabled={selectedRoleId === null || applyState === "submitting"}
            className="btn-primary sticky bottom-4 z-20 w-full"
          >
            {applyState === "submitting" ? "Отправляем..." : "Откликнуться"}
          </button>
        </div>
      )}
      {applyState === "done" && (
        <p className="rounded-lg bg-ok-50 px-4 py-3 text-center text-sm font-medium text-ok-700 animate-scale-in">
          ✓ Отклик отправлен. Можно выбрать другую роль или посмотреть статус во вкладке «Отклики».
        </p>
      )}
      {applyError && <p className="text-sm text-red-500">{applyError}</p>}
    </div>
  );
}
