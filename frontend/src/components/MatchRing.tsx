import { useEffect, useState } from "react";

import { LEVEL_LABELS, type MatchResult, verdictFor } from "@/lib/match";

const SIZE = 96;
const STROKE = 9;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/** Animated circular match score + the skill gap breakdown.

The ring animates once on mount (stroke-dashoffset transition) so the number
"counts up" visually — this is the demo's "aha" beat on the project screen.
*/
export function MatchRing({
  match,
  overallScore,
  loading = false,
}: {
  match: MatchResult | null;
  overallScore?: number | null;
  loading?: boolean;
}) {
  // Start fully empty, then ease to the real value after first paint.
  const [offset, setOffset] = useState(CIRCUMFERENCE);

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
    <div className="card animate-scale-in flex items-center gap-4 overflow-hidden p-4">
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
      </div>
    </div>
  );
}
