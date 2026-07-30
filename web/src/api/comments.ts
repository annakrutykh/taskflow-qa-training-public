import { apiRequest } from "./client";
import type { Comment, Page } from "./types";

export function listComments(taskId: number, limit: number, offset: number) {
  return apiRequest<Page<Comment>>(
    `/tasks/${taskId}/comments?limit=${limit}&offset=${offset}`,
  );
}

export function createComment(taskId: number, text: string) {
  return apiRequest<Comment>(`/tasks/${taskId}/comments`, {
    method: "POST",
    body: { text },
  });
}

export function updateComment(taskId: number, commentId: number, text: string) {
  return apiRequest<Comment>(`/tasks/${taskId}/comments/${commentId}`, {
    method: "PATCH",
    body: { text },
  });
}

export function deleteComment(taskId: number, commentId: number) {
  return apiRequest<void>(`/tasks/${taskId}/comments/${commentId}`, { method: "DELETE" });
}
