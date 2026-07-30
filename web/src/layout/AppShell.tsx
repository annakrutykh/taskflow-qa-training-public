import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import { Button } from "../components";
import { useAuth } from "../context/AuthContext";
import "./AppShell.css";

function initials(firstName: string, lastName: string) {
  return `${firstName[0] ?? ""}${lastName[0] ?? ""}`.toUpperCase();
}

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <div className="app-shell__brand">
          <Link to="/" className="app-shell__logo">
            <img className="app-shell__logo-mark" src="/favicon.svg" alt="" aria-hidden="true" />
            TaskFlow
          </Link>
          {user && (
            <div className="app-shell__nav-group">
              <NavLink
                to="/"
                end
                className={({ isActive }) =>
                  `app-shell__nav-pill${isActive ? " app-shell__nav-pill--active" : ""}`
                }
              >
                <span aria-hidden="true">📁</span> Мои проекты
              </NavLink>
              <NavLink
                to="/tasks"
                className={({ isActive }) =>
                  `app-shell__nav-pill${isActive ? " app-shell__nav-pill--active" : ""}`
                }
              >
                <span aria-hidden="true">🗂️</span> Мои задачи
              </NavLink>
            </div>
          )}
        </div>
        {user && (
          <div className="app-shell__user">
            {user.role === "ADMIN" && (
              <NavLink
                to="/admin"
                className={({ isActive }) =>
                  `app-shell__nav-pill app-shell__nav-pill--accent${isActive ? " app-shell__nav-pill--active" : ""}`
                }
              >
                <span aria-hidden="true">⚙</span> Администрирование
              </NavLink>
            )}
            <NavLink
              to="/profile"
              className={({ isActive }) =>
                `app-shell__profile-link${isActive ? " app-shell__profile-link--active" : ""}`
              }
            >
              <span className="app-shell__avatar">{initials(user.firstName, user.lastName)}</span>
              <span className="app-shell__user-name">
                {user.firstName} {user.lastName}
              </span>
            </NavLink>
            <Button size="sm" variant="ghost" onClick={() => logout()}>
              Выйти
            </Button>
          </div>
        )}
      </header>
      <main className="app-shell__main">{children}</main>
    </div>
  );
}
