import type { ProjectRole, ProjectStatus, TaskPriority, TaskStatus } from "../api/types";

export const STATUS_LABEL: Record<ProjectStatus, { label: string; variant: "success" | "neutral" }> = {
  ACTIVE: { label: "Активен", variant: "success" },
  ARCHIVED: { label: "В архиве", variant: "neutral" },
};

export const ROLE_LABEL: Record<ProjectRole, string> = {
  OWNER: "Владелец",
  MANAGER: "Менеджер",
  VIEWER: "Наблюдатель",
  ADMIN: "Администратор",
};

export const TASK_STATUS_LABEL: Record<TaskStatus, { label: string; variant: "neutral" | "warning" | "success" }> = {
  TODO: { label: "К выполнению", variant: "neutral" },
  IN_PROGRESS: { label: "В работе", variant: "warning" },
  DONE: { label: "Готово", variant: "success" },
};

export const TASK_PRIORITY_LABEL: Record<TaskPriority, { label: string; variant: "neutral" | "warning" | "danger" }> = {
  LOW: { label: "Низкий", variant: "neutral" },
  MEDIUM: { label: "Средний", variant: "warning" },
  HIGH: { label: "Высокий", variant: "danger" },
};

export const USER_ROLE_LABEL: Record<"USER" | "ADMIN", string> = {
  USER: "Пользователь",
  ADMIN: "Администратор",
};
