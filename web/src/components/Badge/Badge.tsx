import type { ReactNode } from "react";
import "./Badge.css";

type Variant = "neutral" | "accent" | "success" | "warning" | "danger";

export function Badge({ variant = "neutral", children }: { variant?: Variant; children: ReactNode }) {
  return <span className={`badge badge--${variant}`}>{children}</span>;
}
