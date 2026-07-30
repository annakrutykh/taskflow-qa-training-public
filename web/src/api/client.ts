const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details: unknown;
    correlationId: string;
    timestamp: string;
  };
}

export class ApiError extends Error {
  code: string;
  status: number;
  details: unknown;
  correlationId: string;

  constructor(status: number, body: ApiErrorBody) {
    super(body.error.message);
    this.name = "ApiError";
    this.code = body.error.code;
    this.status = status;
    this.details = body.error.details;
    this.correlationId = body.error.correlationId;
  }
}

function getToken(): string | null {
  return localStorage.getItem("taskflow_access_token");
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  auth?: boolean;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true } = options;

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json();

  if (!response.ok) {
    throw new ApiError(response.status, data as ApiErrorBody);
  }

  return data as T;
}

interface ValidationErrorItem {
  loc: (string | number)[];
  msg: string;
}

/** Достаёт из ApiError.details (для VALIDATION_ERROR) ошибки по полям формы. */
export function getFieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError) || error.code !== "VALIDATION_ERROR") {
    return {};
  }

  const items = error.details as ValidationErrorItem[] | null;
  if (!Array.isArray(items)) return {};

  const fields: Record<string, string> = {};
  for (const item of items) {
    const field = item.loc[item.loc.length - 1];
    if (typeof field === "string") fields[field] = item.msg;
  }
  return fields;
}

export const auth = {
  getToken,
  setToken(token: string) {
    localStorage.setItem("taskflow_access_token", token);
  },
  clearToken() {
    localStorage.removeItem("taskflow_access_token");
  },
};
