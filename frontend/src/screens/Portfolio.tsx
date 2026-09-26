import { useCallback, useEffect, useState } from "react";

import { createPortfolioLink, getMyPortfolio, type PortfolioItem } from "@/api/portfolio";
import { openExternalLink } from "@/max/webapp";

export function PortfolioScreen() {
  const [items, setItems] = useState<PortfolioItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [linkUrl, setLinkUrl] = useState<string | null>(null);
  const [linkError, setLinkError] = useState<string | null>(null);
  const [creatingLink, setCreatingLink] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = useCallback(() => {
    setError(null);
    setItems(null);
    getMyPortfolio()
      .then(setItems)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Ошибка загрузки"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const createLink = async () => {
    setCreatingLink(true);
    setLinkError(null);
    try {
      const { slug } = await createPortfolioLink();
      const url = `${window.location.origin}/p/${slug}`;
      setLinkUrl(url);
      setCopied(false);
      if (navigator.clipboard?.writeText) {
        try {
          await navigator.clipboard.writeText(url);
          setCopied(true);
        } catch {
          // Embedded webviews may deny clipboard access. The input remains
          // selectable so the user can copy the generated URL manually.
        }
      }
    } catch (err) {
      setLinkError(err instanceof Error ? err.message : "Не удалось создать ссылку");
    } finally {
      setCreatingLink(false);
    }
  };

  return (
    <div className="screen">
      <header>
        <h1 className="screen-title">Портфолио</h1>
        <p className="screen-subtitle">Подтверждённое участие в проектах — то, что покажешь работодателю.</p>
      </header>

      {/* The share card — the loop closes here: experience becomes a link. */}
      <section className="card flex flex-col gap-3 bg-brand-gradient-soft">
        <div>
          <p className="text-sm font-semibold text-slate-900">Отправить работодателю</p>
          <p className="mt-0.5 text-xs leading-snug text-slate-600">
            Публичная страница с подтверждёнными проектами. Без контактов и
            личных данных — только опыт.
          </p>
        </div>
        {linkUrl ? (
          <div className="flex flex-col gap-2">
            <input
              readOnly
              value={linkUrl}
              onFocus={(e) => e.currentTarget.select()}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700"
              aria-label="Ссылка на портфолио"
            />
            <div className="flex items-center gap-2">
              <a
                href={linkUrl}
                target="_blank"
                rel="noreferrer"
                onClick={(event) => {
                  if (openExternalLink(linkUrl)) event.preventDefault();
                }}
                className="btn-primary flex-1 py-2.5"
              >
                Открыть →
              </a>
              <span className={`text-xs ${copied ? "text-emerald-600" : "text-slate-500"}`}>
                {copied ? "скопировано ✓" : "скопируй ссылку вручную"}
              </span>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={createLink}
            disabled={creatingLink}
            className="btn-primary py-2.5"
          >
            {creatingLink ? "Готовим ссылку…" : "Создать ссылку на портфолио"}
          </button>
        )}
        {linkError ? <p className="text-xs text-red-500">{linkError}</p> : null}
      </section>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-600">
          <p>{error}</p>
          <button type="button" onClick={load} className="mt-2 font-medium underline">Повторить</button>
        </div>
      )}

      {!error && items === null && (
        <div className="skeleton h-32" />
      )}

      {items && items.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-gradient-soft text-3xl">🎓</div>
          <p className="text-sm text-slate-400">Пока пусто — здесь появятся завершённые и подтверждённые проекты.</p>
        </div>
      )}

      {items && items.length > 0 && (
        <div className="flex flex-col gap-3">
          {items.map((item) => (
            <div
              key={item.project.id}
              className="card"
            >
              <p className="text-xs text-slate-400">{item.project.organization.name}</p>
              <h2 className="mt-1 text-sm font-semibold">{item.project.title}</h2>
              <p className="mt-1 text-xs text-slate-500">
                Роль: {item.confirmation.role}
                {item.confirmation.contribution && ` · ${item.confirmation.contribution}`}
              </p>
              {item.result && (
                <div className="mt-2 rounded-lg bg-slate-50 p-3">
                  <p className="text-sm font-medium">{item.result.title}</p>
                  <p className="mt-0.5 text-xs text-slate-500">{item.result.description}</p>
                  {item.result.result_url && (
                    <a
                      href={item.result.result_url}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(event) => {
                        if (item.result?.result_url && openExternalLink(item.result.result_url)) {
                          event.preventDefault();
                        }
                      }}
                      className="mt-1 inline-block text-xs text-brand-600 underline"
                    >
                      Ссылка на результат
                    </a>
                  )}
                </div>
              )}
              <p className="mt-2 text-xs text-emerald-600">
                Подтверждено: {item.confirmation.confirmed_by}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
