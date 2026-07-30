import { apiRequest } from "./client";
import type { Page, Task, TaskPriority, TaskStatus } from "./types";

export interface TaskListParams {
  /** Без projectId — задачи из всех проектов, где пользователь участник,
   * плюс назначенные напрямую (см. GET /tasks в docs/API_SPEC.md). */
  projectId?: number;
  /** Дополнительный фильтр поверх базовой видимости (не расширяет её) —
   * например assigneeId=я сузит и без того видимые задачи до "назначено
   * на меня", не откроет доступ к чужим. */
  assigneeId?: number;
  /** Подстрока в title, регистронезависимо (Task.title ILIKE %search%). */
  search?: string;
  limit: number;
  offset: number;
  status?: TaskStatus;
  priority?: TaskPriority;
}

export function listTasks(params: TaskListParams) {
  const query = new URLSearchParams({
    limit: String(params.limit),
    offset: String(params.offset),
  });
  if (params.projectId !== undefined) query.set("projectId", String(params.projectId));
  if (params.assigneeId !== undefined) query.set("assigneeId", String(params.assigneeId));
  if (params.search) query.set("search", params.search);
  if (params.status) query.set("status", params.status);
  if (params.priority) query.set("priority", params.priority);

  return apiRequest<Page<Task>>(`/tasks?${query.toString()}`);
}

export interface TaskCreatePayload {
  projectId: number;
  title: string;
  description?: string;
  priority: TaskPriority;
  assigneeId?: number;
}

export function createTask(payload: TaskCreatePayload) {
  return apiRequest<Task>("/tasks", { method: "POST", body: payload });
}

export interface TaskUpdatePayload {
  title?: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  assigneeId?: number | null;
}

export function updateTask(id: number, payload: TaskUpdatePayload) {
  return apiRequest<Task>(`/tasks/${id}`, { method: "PATCH", body: payload });
}

export function deleteTask(id: number) {
  return apiRequest<void>(`/tasks/${id}`, { method: "DELETE" });
}
