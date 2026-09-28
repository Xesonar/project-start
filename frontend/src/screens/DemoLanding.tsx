import { useState } from "react";

import { authDemo } from "@/api/auth";
import { ApiError } from "@/api/client";
import { setToken } from "@/api/token";
import { getMaxWebApp } from "@/max/webapp";

/**
 * What a judge sees when they open the public link in a browser (no MAX).
 *
 * The whole app is normally locked to the MAX mini-app — this page is the
 * demo door. It is deliberately dark and high-contrast: hackathon demos
 * happen on projectors in lit rooms, where a light UI washes out.
 */
export function DemoLanding({ onDemoReady }: { onDemoReady: () => Promise<void> }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startDemo = async () => {
    setLoading(true);
    setError(null);
    try {
      const { access_token } = await authDemo();
      setToken(access_token);
      await onDemoReady();
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 403
          ? "Веб-доступ отключён. Открой приложение через бота в MAX."
          : err instanceof Error
            ? err.message
            : "Веб-версия временно недоступна",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-full flex-col overflow-hidden bg-slate-950 text-white">
      {/* Ambient glow + grid */}
      <div
        className="pointer-events-none absolute inset-0 opacity-70"
        style={{
          background:
            "radial-gradient(60% 50% at 50% 0%, rgba(53,99,233,0.45) 0%, transparent 70%), radial-gradient(50% 40% at 90% 10%, rgba(139,92,246,0.35) 0%, transparent 70%)",
        }}
      />
      <div className="pointer-events-none absolute inset-0 bg-grid-pattern bg-grid opacity-[0.18]" />

      <div className="relative mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-6 py-12">
        <div className="animate-fade-in-up">
          <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-medium text-brand-200 backdrop-blur">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
            Работает в мессенджере MAX
          </span>

          <h1 className="mt-6 text-4xl font-bold leading-[1.1] tracking-tight">
            Первый проект —
            <br />
            <span className="bg-brand-gradient bg-clip-text text-transparent">
              для каждого студента
            </span>
          </h1>

          <p className="mt-4 text-base leading-relaxed text-slate-300">
            Старт подбирает проекты под навыки и уровень, собирает команду и
            подтверждает участие — так, что портфолио собирается само.
          </p>

          <ul className="mt-8 flex flex-col gap-3 text-sm text-slate-200">
            {[
              ["AI-подбор", "Рекомендации проектов с объяснением, почему это твоё"],
              ["Команда", "Отклики на роли, сбор команды и чат в один клик"],
              ["Портфолио", "Подтверждённый опыт от организатора проекта"],
            ].map(([title, desc]) => (
              <li key={title} className="flex gap-3">
                <span className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-gradient text-[11px] font-bold">
                  ✓
                </span>
                <span>
                  <span className="font-semibold text-white">{title}.</span> {desc}
                </span>
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-10 flex flex-col gap-3">
          <button
            type="button"
            onClick={startDemo}
            disabled={loading}
            className="btn-primary py-4 text-base"
          >
            {loading ? "Готовим демо…" : "Открыть демо →"}
          </button>

          {getMaxWebApp() ? null : (
            <p className="text-center text-xs text-slate-500">
              Демо-режим без установки — посмотрите, как это выглядит у студентов
            </p>
          )}

          {error && (
            <p className="rounded-lg bg-danger-50/10 px-4 py-3 text-center text-sm text-red-300">
              {error}
            </p>
          )}
        </div>
      </div>

        <footer className="relative px-6 pb-10 text-center text-xs text-slate-600">
          Старт · платформа проектных команд · хакатон 2026
        </footer>
    </div>
  );
}
