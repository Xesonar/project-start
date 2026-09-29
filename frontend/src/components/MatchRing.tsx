import { useEffect, useState } from "react";

import { LEVEL_LABELS, type MatchResult, verdictFor } from "@/lib/match";

const SIZE = 96;
const STROKE = 9;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/** Animated circular match score + the skill gap breakdown.

The ring animates once on mount (stroke-dashoffset transition) so the number
"counts up" visually to make the result easier to notice on the project screen.
*/
export function MatchRing({
  match,
  overallScore,
  breakdown,
  loading = false,
}: {
  match: MatchResult | null;
  overallScore?: number | null;
  breakdown?: { skills: number; role: number; specialty: number; difficulty: number };
  loading?: boolean;
}) {
  // Start fully empty, then ease to the real value after first paint.
  const [offset, setOffset] = useState(CIRCUMFERENCE);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    if (!match) return;
    const frame = requestAnimationFrame(() => {
      setOffset(CIRCUMFERENCE * (1 - (overallScore ?? match.score)));
    });
    return () => cancelAnimationFrame(frame);
  }, [match, overallScore]);

  if (loading || !match) {
    return (
      <div className="card flex items-center gap-4">
        <div className="skeleton h-24 w-24 shrink-0 rounded-full" />
        <div className="flex flex-1 flex-col gap-2">
          <div className="skeleton h-4 w-32" />
          <div className="skeleton h-3 w-48" />
        </div>
      </div>
    );
  }

  const { gaps } = match;
  const score = overallScore ?? match.score;
  const verdict = verdictFor(score);
  const percent = Math.round(score * 100);

  return (
    <div className="card animate-scale-in overflow-hidden p-4">
      <div className="flex items-center gap-4">
      <div className="relative shrink-0" style={{ width: SIZE, height: SIZE }}>
        <svg
          width={SIZE}
          height={SIZE}
          viewBox={`0 0 ${SIZE} ${SIZE}`}
          role="img"
          aria-label={`Общее совпадение профиля ${percent} из 100`}
          className="-rotate-90"
        >
          <defs>
            <linearGradient id="match-ring-gradient" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#3563e9" />
              <stop offset="100%" stopColor="#8b5cf6" />
            </linearGradient>
          </defs>
          <circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={RADIUS}
            fill="none"
            stroke="#e2e8f0"
            strokeWidth={STROKE}
          />
          <circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={RADIUS}
            fill="none"
            stroke="url(#match-ring-gradient)"
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 1000ms cubic-bezier(0.16, 1, 0.3, 1)" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xl font-bold tabular-nums text-slate-900">{percent}%</span>
        </div>
      </div>

      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-slate-900">{verdict.title}</p>
        <p className="mt-0.5 text-xs leading-snug text-slate-500">
          Общее совпадение учитывает роль, направление, уровень и навыки. Навыки: {match.covered} из {match.total}. {verdict.hint}
        </p>
        {gaps.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {gaps.slice(0, 4).map((gap) => (
              <span
                key={`${gap.name}-${gap.required_level}`}
                className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700"
                title={gap.status === "missing" ? "Навыка пока нет" : "Уровень ниже нужного"}
              >
                {gap.status === "missing" ? "+" : "↑"} {gap.name}
                <span className="text-amber-500/80">· {LEVEL_LABELS[gap.required_level]}</span>
              </span>
            ))}
          </div>
        ) : (
          <p className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-emerald-600">
            ✓ Полное покрытие навыков
          </p>
        )}
        {breakdown ? (
          <button
            type="button"
            onClick={() => setShowDetails((current) => !current)}
            className="mt-2 text-xs font-medium text-brand-600 underline"
            aria-expanded={showDetails}
          >
            {showDetails ? "Скрыть расчёт" : "Почему такой процент?"}
          </button>
        ) : null}
      </div>
      </div>
      {breakdown && showDetails ? (
        <div className="mt-4 grid grid-cols-2 gap-2 border-t border-slate-100 pt-3 text-xs">
          <ScorePart label="Навыки" value={breakdown.skills} maximum={0.4} />
          <ScorePart label="Роль" value={breakdown.role} maximum={0.25} />
          <ScorePart label="Направление" value={breakdown.specialty} maximum={0.2} />
          <ScorePart label="Уровень" value={breakdown.difficulty} maximum={0.15} />
        </div>
      ) : null}
    </div>
  );
}

function ScorePart({ label, value, maximum }: { label: string; value: number; maximum: number }) {
  return (
    <div className="rounded-lg bg-slate-50 p-2.5 dark:bg-slate-800">
      <div className="flex items-center justify-between gap-2">
        <span className="text-slate-500">{label}</span>
        <strong className="tabular-nums text-slate-900">
          {Math.round(value * 100)}/{Math.round(maximum * 100)}
        </strong>
      </div>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
        <div
          className="h-full rounded-full bg-brand-gradient"
          style={{ width: `${Math.min(100, (value / maximum) * 100)}%` }}
        />
      </div>
    </div>
  );
}
