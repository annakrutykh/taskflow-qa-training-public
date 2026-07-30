import { apiRequest } from "./client";
import type { TokenResponse, User } from "./types";

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  firstName: string;
  lastName: string;
}

export function login(payload: LoginPayload) {
  return apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: payload,
    auth: false,
  });
}

export function register(payload: RegisterPayload) {
  return apiRequest<User>("/auth/register", {
    method: "POST",
    body: payload,
    auth: false,
  });
}

export function logout() {
  return apiRequest<void>("/auth/logout", { method: "POST" });
}

export function getMe() {
  return apiRequest<User>("/users/me");
}

export interface UpdateProfilePayload {
  firstName?: string;
  lastName?: string;
}

export function updateProfile(payload: UpdateProfilePayload) {
  return apiRequest<User>("/users/me", { method: "PATCH", body: payload });
}
