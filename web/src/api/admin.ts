import { apiRequest } from "./client";

/** ADMIN-only. Необратимо — полностью очищает БД и заново засеивает из seed.py. */
export function resetDatabase() {
  return apiRequest<void>("/admin/reset", { method: "POST" });
}
