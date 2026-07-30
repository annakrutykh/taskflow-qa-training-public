import { apiRequest } from "./client";
import type { Page, User, UserSearchResult } from "./types";

/** ADMIN-only per API_SPEC.md — обычным участникам проекта эта ручка недоступна. */
export function listUsers(limit: number, offset: number) {
  return apiRequest<Page<User>>(`/users?limit=${limit}&offset=${offset}`);
}

/** Доступно любому авторизованному — минимальные поля, для поиска при добавлении в
 *  проект или выборе исполнителя задачи. */
export function searchUsers(query: string, limit = 20) {
  return apiRequest<UserSearchResult[]>(
    `/users/search?q=${encodeURIComponent(query)}&limit=${limit}`,
  );
}

/** ADMIN-only. */
export function updateUserRole(id: number, role: "USER" | "ADMIN") {
  return apiRequest<User>(`/users/${id}/role`, { method: "PATCH", body: { role } });
}

/** ADMIN-only. */
export function updateUserStatus(id: number, isActive: boolean) {
  return apiRequest<User>(`/users/${id}/status`, {
    method: "PATCH",
    body: { isActive },
  });
}

/** ADMIN-only. 409 LAST_PROJECT_OWNER, если пользователь — последний OWNER проекта. */
export function deleteUser(id: number) {
  return apiRequest<void>(`/users/${id}`, { method: "DELETE" });
}
