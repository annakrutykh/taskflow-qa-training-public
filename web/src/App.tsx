import { Route, Routes } from "react-router-dom";
import { ProjectsList } from "./pages/Projects/ProjectsList";
import { ProjectDetail } from "./pages/Projects/ProjectDetail";
import { MyTasksPage } from "./pages/Tasks/MyTasksPage";
import { ProfilePage } from "./pages/Profile/ProfilePage";
import { AdminPage } from "./pages/Admin/AdminPage";
import { LoginForm } from "./components/auth/LoginForm";
import { RegisterForm } from "./components/auth/RegisterForm";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AppShell } from "./layout/AppShell";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginForm />} />
      <Route path="/register" element={<RegisterForm />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppShell>
              <ProjectsList />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:id"
        element={
          <ProtectedRoute>
            <AppShell>
              <ProjectDetail />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/tasks"
        element={
          <ProtectedRoute>
            <AppShell>
              <MyTasksPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <AppShell>
              <ProfilePage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            <AppShell>
              <AdminPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
