import type { HTMLAttributes, ReactNode } from "react";
import "./Card.css";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  padded?: boolean;
  interactive?: boolean;
  children: ReactNode;
}

export function Card({
  padded = true,
  interactive = false,
  className,
  children,
  ...rest
}: CardProps) {
  const classes = [
    "card",
    padded ? "card--padded" : "",
    interactive ? "card--interactive" : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={classes} {...rest}>
      {children}
    </div>
  );
}
