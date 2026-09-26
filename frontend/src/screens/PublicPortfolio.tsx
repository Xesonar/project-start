import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { ApiError } from "@/api/client";
import { getPublicPortfolio, type PublicPortfolio } from "@/api/portfolio";
import { getMaxWebApp } from "@/max/webapp";

const LEVEL_LABELS: Record<string, string> = {
  beginner: "Начинающий",
  intermediate: "Средний",
  advanced: "Продвинутый",
};

const SKILL_LEVEL_LABELS: Record<string, string> = {
  beginner: "начальный",
  intermediate: "средний",
  advanced: "продвинутый",
};

function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/** Public portfolio page — what a recruiter or a teacher opens.

Deliberately its own dark surface, not the student app: no bottom nav, no
auth, no editing. It reads like a finished product page, because that is
the promise the app makes ("портфолио собирается само").
*/
export function PublicPortfolioScreen() {
  const { slug } = useParams<{ slug: string }>();
  const [portfolio, setPortfolio] = useState<PublicPortfolio | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [shareStatus, setShareStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;
    getPublicPortfolio(slug)
      .then((data) => setPortfolio(data))
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 404) {
          setNotFound(true);
          return;
        }
        setLoadError(err instanceof Error ? err.message : "Не удалось загрузить портфолио");
      });
  }, [slug]);

  if (notFound || !slug) {
    return (
      <div className="relative flex min-h-full flex-col items-center justify-center overflow-hidden bg-slate-950 px-6 text-center text-white">
        <div
          className="pointer-events-none absolute inset-0 opacity-60"
          style={{
            background:
              "radial-gradient(60% 50% at 50% 0%, rgba(53,99,233,0.4) 0%, transparent 70%)",
          }}
        />
        <div className="relative">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-gradient text-3xl">
            🛰
          </div>
          <h1 className="mt-5 text-2xl font-bold">Такого портфолио нет</h1>
          <p className="mt-2 max-w-xs text-sm text-slate-400">
            Возможно, ссылка устарела или ещё не создана. Попросите студента
            отправить новую.
          </p>
          <a
            href="/"
            className="mt-6 inline-block text-sm font-medium text-brand-300 underline"
          >
            Вернуться в Старт
          </a>
        </div>
      </div>
    );
  }

  if (!portfolio) {
    if (loadError) {
      return (
        <div className="flex min-h-full flex-col items-center justify-center bg-slate-950 px-6 text-center text-white">
          <h1 className="text-xl font-bold">Портфолио временно недоступно</h1>
          <p className="mt-2 max-w-xs text-sm text-slate-400">{loadError}</p>
          <button type="button" onClick={() => window.location.reload()} className="btn-primary mt-6">
            Попробовать снова
          </button>
        </div>
      );
    }
    return (
      <div className="mx-auto flex max-w-md flex-col gap-4 px-4 py-8">
        <div className="skeleton h-24 rounded-2xl" />
        <div className="skeleton h-40 rounded-2xl" />
        <div className="skeleton h-40 rounded-2xl" />
      </div>
    );
  }

  const initials = portfolio.name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();

  const share = async () => {
    const url = window.location.href;
    setShareStatus(null);
    try {
      const max = getMaxWebApp();
      if (max?.shareMaxContent) {
        max.shareMaxContent({
          text: `Подтверждённое портфолио ${portfolio.name}`,
          link: url,
        });
        return;
      }
      if (navigator.share) {
        await navigator.share({ title: `Портфолио · ${portfolio.name}`, url });
        return;
      }
      if (!navigator.clipboard?.writeText) throw new Error("Копирование недоступно");
      await navigator.clipboard.writeText(url);
      setShareStatus("Ссылка скопирована");
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setShareStatus("Не удалось поделиться — скопируй адрес страницы вручную");
    }
  };

  return (
    <div className="relative min-h-full overflow-hidden bg-slate-950 text-white">
      <div
        className="pointer-events-none absolute inset-0 opacity-70"
        style={{
          background:
            "radial-gradient(55% 45% at 15% 0%, rgba(53,99,233,0.4) 0%, transparent 70%), radial-gradient(50% 40% at 95% 5%, rgba(139,92,246,0.32) 0%, transparent 70%)",
        }}
      />
      <div className="pointer-events-none absolute inset-0 bg-grid-pattern bg-grid opacity-[0.14]" />

      <div className="relative mx-auto flex max-w-md flex-col gap-6 px-5 pb-16 pt-[max(2rem,env(safe-area-inset-top))]">
        {/* Header */}
        <header className="animate-fade-in-up">
          <div className="flex items-center gap-4">
            {portfolio.avatar_url ? (
              <img
                src={portfolio.avatar_url}
                alt={portfolio.name}
                className="h-16 w-16 rounded-2xl object-cover ring-2 ring-white/20"
              />
            ) : (
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-gradient text-xl font-bold ring-2 ring-white/20">
                {initials}
              </div>
            )}
            <div className="min-w-0">
              <h1 className="text-2xl font-bold leading-tight tracking-tight">
                {portfolio.name}
              </h1>
              <p className="mt-0.5 text-sm text-slate-400">
                {[
                  portfolio.specialty,
                  portfolio.experience_level && LEVEL_LABELS[portfolio.experience_level],
                ]
                  .filter(Boolean)
                  .join(" · ") || "Студент"}
              </p>
            </div>
          </div>
          {portfolio.preferred_role ? (
            <p className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium text-brand-200">
              Хочу расти как {portfolio.preferred_role}
            </p>
          ) : null}
        </header>

        {/* Skills */}
        {portfolio.skills.length > 0 ? (
          <section className="animate-fade-in-up">
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Навыки
            </h2>
            <div className="flex flex-wrap gap-2">
              {portfolio.skills.map((skill) => (
                <span
                  key={skill.name}
                  className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium text-slate-200"
                >
                  {skill.name}{" "}
                  <span className="text-slate-500">· {SKILL_LEVEL_LABELS[skill.level]}</span>
                </span>
              ))}
            </div>
          </section>
        ) : null}

        {/* Projects */}
        <section className="flex flex-col gap-3">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Подтверждённые проекты
          </h2>

          {portfolio.projects.length === 0 ? (
            <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-8 text-center">
              <p className="text-sm text-slate-400">
                Пока нет завершённых проектов. Первое подтверждение появится
                здесь, как только организатор закроет проект.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {portfolio.projects.map((item) => (
                <div
                  key={`${item.project_title}-${item.confirmed_at}`}
                  className="rounded-2xl border border-white/10 bg-white/[0.06] p-4 backdrop-blur-sm transition duration-200 ease-out-expo hover:border-white/20 hover:bg-white/[0.09]"
                >
                  <p className="text-xs text-slate-500">{item.organization}</p>
                  <h3 className="mt-1 text-base font-bold leading-snug">
                    {item.project_title}
                  </h3>
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                    <span className="rounded-full bg-brand-gradient px-2.5 py-0.5 font-semibold text-white">
                      {item.role}
                    </span>
                    <span className="text-slate-500">{formatDate(item.confirmed_at)}</span>
                  </div>
                  {item.contribution ? (
                    <p className="mt-2 text-sm text-slate-300">{item.contribution}</p>
                  ) : null}
                  {item.result ? (
                    <div className="mt-3 rounded-lg bg-black/20 p-3">
                      <p className="text-sm font-medium text-white">{item.result.title}</p>
                      <p className="mt-0.5 text-xs text-slate-400">
                        {item.result.description}
                      </p>
                      {item.result.result_url ? (
                        <a
                          href={item.result.result_url}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-1.5 inline-block text-xs font-medium text-brand-300 underline"
                        >
                          Смотреть результат →
                        </a>
                      ) : null}
                    </div>
                  ) : null}
                  <p className="mt-2.5 inline-flex items-center gap-1 text-xs font-medium text-emerald-400">
                    <span aria-hidden="true">✓</span> Подтверждено организатором
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>

        <button
          type="button"
          onClick={() => void share()}
          className="btn-primary"
        >
          Поделиться портфолио
        </button>
        {shareStatus ? (
          <p role="status" className="-mt-3 text-center text-xs text-slate-400">{shareStatus}</p>
        ) : null}

        <footer className="text-center text-xs text-slate-600">
          Старт · подтверждённый опыт студентов · хакатон 2026
        </footer>
      </div>
    </div>
  );
}
