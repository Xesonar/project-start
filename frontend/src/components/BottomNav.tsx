import { useCallback, useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useUnseenDecidedApplicationsCount } from "@/features/notifications";
import { hapticSelect } from "@/lib/haptics";
import { isDarkTheme, subscribeToTheme, toggleTheme } from "@/lib/theme";
import { useMaxBackButton } from "@/max/useMaxBackButton";

type IconProps = { className?: string; badge?: number };

function HomeIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M4 11.5 12 4l8 7.5V20a1 1 0 0 1-1 1h-4v-6H9v6H5a1 1 0 0 1-1-1v-8.5Z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SearchIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="11" cy="11" r="6.5" stroke="currentColor" strokeWidth="1.7" />
      <path
        d="m16 16 4.5 4.5"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  );
}

function InboxIcon({ className, badge }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M4 13h4l1.5 3h5L16 13h4"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M4 13V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v7l-2.5 7H6.5L4 13Z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {badge ? (
        <circle cx="18" cy="5.5" r="3.5" fill="#ef4444" stroke="white" strokeWidth="1.2" />
      ) : null}
    </svg>
  );
}

function UsersIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="9" cy="8" r="3.2" stroke="currentColor" strokeWidth="1.7" />
      <path
        d="M3 20c0-3.3 2.7-5 6-5s6 1.7 6 5"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      <path
        d="M16 5.5a3.2 3.2 0 0 1 0 6m1.5 3.6c1.9.5 3.5 1.8 3.5 4.4"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  );
}

function FolderIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M3 8.5A2 2 0 0 1 5 6.5h3.2l1.5 2H19a2 2 0 0 1 2 2V18a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8.5Z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
    </svg>
  );
}

const TABS = [
  { to: "/", label: "Главная", end: true, Icon: HomeIcon },
  { to: "/catalog", label: "Поиск", end: false, Icon: SearchIcon },
  { to: "/applications", label: "Отклики", end: false, Icon: InboxIcon },
  { to: "/team", label: "Команда", end: false, Icon: UsersIcon },
  { to: "/portfolio", label: "Портфолио", end: false, Icon: FolderIcon },
];

export function AppLayout() {
  const unseenCount = useUnseenDecidedApplicationsCount();
  const location = useLocation();
  const navigate = useNavigate();
  const goHome = useCallback(() => navigate("/"), [navigate]);
  useMaxBackButton(goHome, location.pathname === "/assessment");

  return (
    <div className="flex min-h-full flex-col">
      <main className="flex-1">
        <Outlet />
      </main>
      {location.pathname === "/" ? <ThemeToggle /> : null}
      <nav
        aria-label="Основная навигация"
        className="fixed inset-x-0 bottom-0 z-50 border-t border-slate-200 bg-white/90 pb-safe backdrop-blur-lg dark:border-slate-700 dark:bg-slate-900/90"
      >
        <div className="mx-auto flex max-w-md">
          {TABS.map(({ to, label, end, Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => hapticSelect()}
              aria-label={label}
              className={({ isActive }) =>
                `relative flex flex-1 flex-col items-center gap-1 py-2.5 transition-colors duration-200 ${
                  isActive ? "text-brand-600" : "text-slate-400"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span className="absolute top-0 h-0.5 w-8 rounded-full bg-brand-gradient" />
                  )}
                  <Icon className="h-6 w-6" badge={unseenCount} />
                  <span className="text-[10px] font-medium">{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}

function ThemeToggle() {
  const [dark, setDark] = useState(isDarkTheme);

  useEffect(() => subscribeToTheme(setDark), []);

  return (
    <button
      type="button"
      onClick={() => {
        hapticSelect();
        setDark(toggleTheme() === "dark");
      }}
      aria-label={dark ? "Включить светлую тему" : "Включить тёмную тему"}
      title={dark ? "Светлая тема" : "Тёмная тема"}
      className="fixed bottom-[calc(max(0px,env(safe-area-inset-bottom))+5rem)] right-[max(1rem,calc((100vw-28rem)/2-3.5rem))] z-40 flex h-11 w-11 items-center justify-center rounded-full border border-slate-200 bg-white/95 text-xl text-slate-600 shadow-lift backdrop-blur transition active:scale-95 dark:border-slate-700 dark:bg-slate-900/95 dark:text-amber-300"
    >
      <span className="leading-none" aria-hidden="true">{dark ? "☀" : "☾"}</span>
    </button>
  );
}
