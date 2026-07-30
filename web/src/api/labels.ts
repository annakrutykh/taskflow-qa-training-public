import { apiRequest } from "./client";
import type { Label, Page } from "./types";

export function listLabels(limit: number, offset: number) {
  return apiRequest<Page<Label>>(`/labels?limit=${limit}&offset=${offset}`);
}

/** ADMIN-only per API_SPEC.md. */
export function createLabel(name: string) {
  return apiRequest<Label>("/labels", { method: "POST", body: { name } });
}

/** ADMIN-only per API_SPEC.md — удаляет метку целиком, вместе со всеми привязками. */
export function deleteLabel(id: number) {
  return apiRequest<void>(`/labels/${id}`, { method: "DELETE" });
}

/** MANAGER+/ADMIN. Идемпотентно. */
export function attachLabel(taskId: number, labelId: number) {
  return apiRequest<void>(`/tasks/${taskId}/labels/${labelId}`, { method: "POST" });
}

/** MANAGER+/ADMIN. Идемпотентно. */
export function detachLabel(taskId: number, labelId: number) {
  return apiRequest<void>(`/tasks/${taskId}/labels/${labelId}`, { method: "DELETE" });
}
