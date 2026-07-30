export interface User {
  id: number;
  email: string;
  firstName: string;
  lastName: string;
  role: "USER" | "ADMIN";
  isActive: boolean;
}

export interface UserSearchResult {
  id: number;
  firstName: string;
  lastName: string;
  email: string;
  role: "USER" | "ADMIN";
}

export interface TokenResponse {
  accessToken: string;
  tokenType: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
  hasNext: boolean;
}

export type ProjectStatus = "ACTIVE" | "ARCHIVED";
export type ProjectRole = "OWNER" | "MANAGER" | "VIEWER" | "ADMIN";

export interface Project {
  id: number;
  name: string;
  description: string | null;
  status: ProjectStatus;
  ownerId: number;
}

export interface ProjectMember {
  userId: number;
  role: ProjectRole;
  firstName: string;
  lastName: string;
}

export type TaskStatus = "TODO" | "IN_PROGRESS" | "DONE";
export type TaskPriority = "LOW" | "MEDIUM" | "HIGH";

export interface Label {
  id: number;
  name: string;
}

export interface Task {
  id: number;
  projectId: number;
  projectName: string;
  assigneeId: number | null;
  assigneeFirstName: string | null;
  assigneeLastName: string | null;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  labels: Label[];
  commentsCount: number;
}

export interface Comment {
  id: number;
  taskId: number;
  authorId: number;
  authorFirstName: string;
  authorLastName: string;
  text: string;
}
