import "./Skeleton.css";

interface SkeletonProps {
  width?: string;
  height?: string;
  radius?: string;
  className?: string;
}

export function Skeleton({ width = "100%", height = "1rem", radius, className }: SkeletonProps) {
  return (
    <span
      className={["skeleton", className ?? ""].filter(Boolean).join(" ")}
      style={{ width, height, borderRadius: radius }}
      aria-hidden="true"
    />
  );
}

export function SkeletonRows({ count = 5, height = "2.5rem" }: { count?: number; height?: string }) {
  return (
    <div className="skeleton-rows">
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} height={height} radius="var(--radius-md)" />
      ))}
    </div>
  );
}
