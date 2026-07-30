import type { ReactNode } from 'react';
import './AuthLayout.css';

interface AuthLayoutProps {
  eyebrow: string;
  title: string;
  subtitle: string;
  children: ReactNode;
}

/**
 * Shared shell for /login and /register.
 * Left: editorial pitch + decorative grid (pure CSS, no images).
 * Right: the form card, passed in as children.
 */
export function AuthLayout({ eyebrow, title, subtitle, children }: AuthLayoutProps) {
  return (
    <div className="auth-shell">
      <aside className="auth-pitch">
        <div className="auth-pitch__grid" aria-hidden="true" />
        <div className="auth-pitch__content">
          <span className="auth-pitch__eyebrow">{eyebrow}</span>
          <h1 className="auth-pitch__title">{title}</h1>
          <p className="auth-pitch__subtitle">{subtitle}</p>
          <div className="auth-pitch__meta">
            <span className="auth-pitch__dot" />
            <span>practice environment · real endpoints · real bugs</span>
          </div>
        </div>
      </aside>

      <main className="auth-form-side">
        <div className="auth-card">{children}</div>
      </main>
    </div>
  );
}
