import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { clearAdminToken, getAdminToken } from "@/api/token";
import { ADMIN_UNAUTHORIZED_EVENT } from "@/api/client";
import { AdminLogin } from "@/screens/admin/AdminLogin";
import { AdminMetricsScreen } from "@/screens/admin/AdminMetrics";
import { AdminProjectApplications } from "@/screens/admin/AdminProjectApplications";
import { AdminProjectCreate } from "@/screens/admin/AdminProjectCreate";
import { AdminProjectList } from "@/screens/admin/AdminProjectList";

export function AdminApp() {
  const [loggedIn, setLoggedIn] = useState(() => getAdminToken() !== null);

  useEffect(() => {
    const handleUnauthorized = () => setLoggedIn(false);
    window.addEventListener(ADMIN_UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => window.removeEventListener(ADMIN_UNAUTHORIZED_EVENT, handleUnauthorized);
  }, []);

  if (!loggedIn) {
    return <AdminLogin onLoggedIn={() => setLoggedIn(true)} />;
  }

  const logout = () => {
    clearAdminToken();
    setLoggedIn(false);
  };

  return (
    <div className="min-h-full">
      <div className="mx-auto flex max-w-2xl justify-end px-4 pt-3">
        <button type="button" onClick={logout} className="text-xs text-slate-500 underline">
          Выйти из админки
        </button>
      </div>
      <Routes>
        <Route path="/" element={<Navigate to="metrics" replace />} />
        <Route path="metrics" element={<AdminMetricsScreen />} />
        <Route path="projects" element={<AdminProjectList />} />
        <Route path="projects/new" element={<AdminProjectCreate />} />
        <Route path="projects/:id" element={<AdminProjectApplications />} />
        <Route path="*" element={<Navigate to="metrics" replace />} />
      </Routes>
    </div>
  );
}
