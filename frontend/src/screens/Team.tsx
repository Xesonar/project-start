import { useEffect, useState } from "react";

import { ApiError } from "@/api/client";
import { getMyTeam, type Team } from "@/api/team";
import { getMaxWebApp } from "@/max/webapp";

function openTeamChat(url: string) {
  const webApp = getMaxWebApp();
  if (webApp) {
    webApp.openMaxLink(url);
  } else {
    window.open(url, "_blank", "noopener,noreferrer");
  }
}

export function TeamScreen() {
  const [team, setTeam] = useState<Team | null>(null);
  const [notInTeam, setNotInTeam] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    setNotInTeam(false);
    setTeam(null);
    getMyTeam()
      .then(setTeam)
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 404) {
          setNotInTeam(true);
          return;
        }
        setError(err instanceof Error ? err.message : "Ошибка загрузки");
      });
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="screen">
      <header>
        <h1 className="screen-title">Моя команда</h1>
        <p className="screen-subtitle">С кем ты делаешь проект прямо сейчас.</p>
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

      {!error && !notInTeam && team === null && (
        <div className="skeleton h-32" />
      )}

      {team && (
        <>
          <div className="card">
            <p className="text-xs text-slate-400">{team.project.organization.name}</p>
            <h2 className="mt-1 text-sm font-semibold">{team.project.title}</h2>
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
        </>
      )}
    </div>
  );
}
