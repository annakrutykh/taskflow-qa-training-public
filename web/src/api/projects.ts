import { apiRequest } from "./client";
import type { Page, Project, ProjectMember, ProjectRole } from "./types";

export function listProjects(limit: number, offset: number) {
  return apiRequest<Page<Project>>(`/projects?limit=${limit}&offset=${offset}`);
}

export function getProject(id: number) {
  return apiRequest<Project>(`/projects/${id}`);
}

export interface ProjectCreatePayload {
  name: string;
  description?: string;
}

export function createProject(payload: ProjectCreatePayload) {
  return apiRequest<Project>("/projects", { method: "POST", body: payload });
}

export interface ProjectUpdatePayload {
  name?: string;
  description?: string;
  status?: "ACTIVE" | "ARCHIVED";
}

export function updateProject(id: number, payload: ProjectUpdatePayload) {
  return apiRequest<Project>(`/projects/${id}`, { method: "PATCH", body: payload });
}

export function deleteProject(id: number) {
  return apiRequest<void>(`/projects/${id}`, { method: "DELETE" });
}

export function listMembers(projectId: number, limit: number, offset: number) {
  return apiRequest<Page<ProjectMember>>(
    `/projects/${projectId}/members?limit=${limit}&offset=${offset}`,
  );
}

export function addMember(projectId: number, userId: number, role: ProjectRole) {
  return apiRequest<ProjectMember>(`/projects/${projectId}/members`, {
    method: "POST",
    body: { userId, role },
  });
}

export function updateMemberRole(projectId: number, userId: number, role: ProjectRole) {
  return apiRequest<ProjectMember>(`/projects/${projectId}/members/${userId}`, {
    method: "PATCH",
    body: { role },
  });
}

export function removeMember(projectId: number, userId: number) {
  return apiRequest<void>(`/projects/${projectId}/members/${userId}`, { method: "DELETE" });
}
