import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listRecommendedProjects, type ProjectRecommendation } from "@/api/projects";
import { getMySkills, type UserSkill } from "@/api/users";
import { ProjectCard } from "@/components/ProjectCard";
import { useAuth } from "@/app/AuthProvider";
import { LEARNING_BY_ROLE } from "@/features/learning";
import { ROLES, type AssessmentRole } from "@/features/assessment";
import { openExternalLink } from "@/max/webapp";

export function HomeScreen() {
  const { me } = useAuth();
  const [projects, setProjects] = useState<ProjectRecommendation[] | null>(null);
  const [skills, setSkills] = useState<UserSkill[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    setProjects(null);
    setSkills(null);
    Promise.all([listRecommendedProjects(), getMySkills()])
      .then(([projectItems, skillItems]) => {
        setProjects(projectItems);
        setSkills(skillItems);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Ошибка загрузки"));
  };

  useEffect(() => {
    load();
  }, []);

  const top = projects?.[0];
  const hasAssessment = Boolean(me?.profile?.preferred_role);
  const isStarter = skills !== null && (skills.length === 0 || Math.max(...skills.map((item) => item.rating)) <= 1);
  const profileRole = ROLES.includes(me?.profile?.preferred_role as AssessmentRole)
    ? (me?.profile?.preferred_role as AssessmentRole)
    : "Frontend developer";
  const learningResources = LEARNING_BY_ROLE[profileRole];

  return (
    <div className="screen">
      <header className="animate-fade-in-up">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm font-medium text-slate-400">Привет, {me?.name} 👋</p>
          <Link to="/assessment" className="text-xs font-medium text-brand-600">
            {hasAssessment ? "Обновить навыки" : "Оценить навыки"}
          </Link>
        </div>
        <h1 className="screen-title">Твой подбор</h1>
        <p className="screen-subtitle">
          Проекты, которые подходят тебе больше всего — по навыкам, уровню и роли.
        </p>
      </header>

      {error ? (
        <div className="rounded-lg border border-danger-50 bg-danger-50 p-4 text-sm text-danger-700">
          <p>{error}</p>
          <button type="button" onClick={load} className="mt-2 font-medium underline">
            Повторить
          </button>
        </div>
      ) : null}

      {!error && projects === null ? (
        <div className="flex flex-col gap-3">
          {[72, 96, 84].map((h, i) => (
            <div key={i} className="skeleton" style={{ height: h }} />
          ))}
        </div>
      ) : null}

      {!error && projects !== null && projects.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-gradient-soft text-3xl">
            🚀
          </div>
          <p className="text-sm text-slate-400">
            {isStarter
              ? "Сейчас нет открытых проектов начального уровня. Материалы для подготовки доступны после повторной оценки навыков."
              : "Пока нет открытых проектов — загляни на вкладку «Поиск» позже."}
          </p>
          {isStarter && (
            <div className="mt-2 flex w-full flex-col gap-2 text-left">
              {learningResources.map((resource) => (
                <a
                  key={resource.url}
                  href={resource.url}
                  target="_blank"
                  rel="noreferrer"
                  onClick={(event) => {
                    if (openExternalLink(resource.url)) event.preventDefault();
                  }}
                  className="rounded-lg border border-brand-200 bg-brand-gradient-soft p-3 text-sm"
                >
                  <span className="font-semibold text-brand-700">{resource.title} ↗</span>
                  <span className="mt-0.5 block text-xs text-slate-500">{resource.description}</span>
                </a>
              ))}
            </div>
          )}
        </div>
      ) : null}

      {!error && projects !== null && projects.length > 0 ? (
        <div className="stagger flex flex-col gap-3">
          {isStarter ? (
            <section className="rounded-xl border border-brand-200 bg-brand-gradient-soft p-4 dark:border-brand-800 dark:bg-slate-900">
              <h2 className="font-semibold text-brand-800 dark:text-brand-200">Сначала немного прокачаем базу</h2>
              <p className="mt-1 text-sm text-brand-700 dark:text-slate-300">
                Мы показываем тебе только начальные проекты. Эти материалы помогут быстрее войти в выбранную роль.
              </p>
              <div className="mt-3 flex flex-col gap-2">
                {learningResources.map((resource) => (
                  <a
                    key={resource.url}
                    href={resource.url}
                    target="_blank"
                    rel="noreferrer"
                    onClick={(event) => {
                      if (openExternalLink(resource.url)) event.preventDefault();
                    }}
                    className="rounded-lg border border-brand-200 bg-white/80 p-3 text-sm transition hover:border-brand-300 dark:border-slate-700 dark:bg-slate-800/90 dark:hover:border-brand-500"
                  >
                    <span className="font-semibold text-brand-700 dark:text-brand-300">{resource.title} ↗</span>
                    <span className="mt-0.5 block text-xs text-slate-500 dark:text-slate-400">{resource.description}</span>
                  </a>
                ))}
              </div>
            </section>
          ) : null}
          {top?.reason ? (
            <div className="rounded-lg bg-brand-gradient-soft px-3 py-3 text-xs text-brand-700 dark:bg-slate-900 dark:text-brand-200">
              <p className="flex gap-2">
                <span aria-hidden="true">✦</span>
                <span>
                  Лучшее совпадение — <span className="font-semibold">{top.title}</span>.{" "}
                  {top.reason}
                </span>
              </p>
              <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 border-t border-brand-200/60 pt-2 text-[11px] dark:border-brand-800">
                <span>Навыки: {Math.round(top.breakdown.skills * 100)}/40</span>
                <span>Роль: {Math.round(top.breakdown.role * 100)}/25</span>
                <span>Направление: {Math.round(top.breakdown.specialty * 100)}/20</span>
                <span>Уровень: {Math.round(top.breakdown.difficulty * 100)}/15</span>
              </div>
            </div>
          ) : null}
          {projects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
