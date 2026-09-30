import { Navigate, Route, BrowserRouter, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import DashboardLayout from "./pages/DashboardLayout.jsx";
import OverviewPage from "./pages/OverviewPage.jsx";
import AppointmentsPage from "./pages/AppointmentsPage.jsx";
import ServicesPage from "./pages/ServicesPage.jsx";
import LeadsPage from "./pages/LeadsPage.jsx";
import SettingsPage from "./pages/SettingsPage.jsx";
import KnowledgePage from "./pages/KnowledgePage.jsx";
import CalendarPage from "./pages/CalendarPage.jsx";

function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-loading">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function RedirectIfAuthed({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-loading">Loading…</div>;
  if (user) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter basename="/admin">
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<RedirectIfAuthed><LoginPage /></RedirectIfAuthed>} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <DashboardLayout />
              </RequireAuth>
            }
          >
            <Route index element={<OverviewPage />} />
            <Route path="appointments" element={<AppointmentsPage />} />
            <Route path="appointments/:id" element={<AppointmentsPage />} />
            <Route path="calendar" element={<CalendarPage />} />
            <Route path="services" element={<ServicesPage />} />
            <Route path="services/:id" element={<ServicesPage />} />
            {/* Webhooks moved under Settings — keep old links/bookmarks working */}
            <Route path="webhooks" element={<Navigate to="/settings/webhooks" replace />} />
            {/* Pages moved under Settings — keep old links/bookmarks working */}
            <Route path="pages" element={<Navigate to="/settings/pages" replace />} />
            <Route path="leads" element={<LeadsPage />} />
            <Route path="leads/:id" element={<LeadsPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="settings/:category" element={<SettingsPage />} />
            <Route path="knowledge" element={<KnowledgePage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
