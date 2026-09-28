import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AuthProvider, useAuth } from "@/app/AuthProvider";
import { AppLayout } from "@/components/BottomNav";
import { AdminApp } from "@/screens/admin/AdminApp";
import { CatalogScreen } from "@/screens/Catalog";
import { HomeScreen } from "@/screens/Home";
import { MyApplicationsScreen } from "@/screens/MyApplications";
import { OnboardingScreen } from "@/screens/Onboarding";
import { PortfolioScreen } from "@/screens/Portfolio";
import { PublicPortfolioScreen } from "@/screens/PublicPortfolio";
import { ProjectDetailScreen } from "@/screens/ProjectDetail";
import { TeamScreen } from "@/screens/Team";

function StudentShell() {
  const { status, me, errorMessage, refreshMe } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return <CenteredMessage>Загружаем...</CenteredMessage>;
  }

  if (status === "unavailable") {
    return (
      <CenteredMessage>
        Откройте приложение из чата с ботом в MAX.
      </CenteredMessage>
    );
  }

  if (status === "error") {
    return <CenteredMessage>Не удалось войти: {errorMessage}</CenteredMessage>;
  }

  if (!me?.profile?.preferred_role && location.pathname !== "/assessment") {
    return <Navigate to="/assessment" replace />;
  }

  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<HomeScreen />} />
        <Route path="/catalog" element={<CatalogScreen />} />
        <Route path="/applications" element={<MyApplicationsScreen />} />
        <Route path="/team" element={<TeamScreen />} />
        <Route path="/portfolio" element={<PortfolioScreen />} />
        <Route
          path="/assessment"
          element={<OnboardingScreen retake={Boolean(me?.profile?.preferred_role)} />}
        />
      </Route>
      <Route path="/projects/:id" element={<ProjectDetailScreen />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function CenteredMessage({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-full items-center justify-center px-6 text-center text-sm text-slate-500">
      {children}
    </div>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/admin/*"
          element={<AdminApp />}
        />
        {/* Public portfolio — no auth, this is the recruiter's link. */}
        <Route path="/p/:slug" element={<PublicPortfolioScreen />} />
        <Route
          path="/*"
          element={
            <AuthProvider>
              <StudentShell />
            </AuthProvider>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
