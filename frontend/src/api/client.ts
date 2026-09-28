import { clearAdminToken, clearToken, getAdminToken, getToken } from "./token";

export const ADMIN_UNAUTHORIZED_EVENT = "project-start:admin-unauthorized";
export const STUDENT_UNAUTHORIZED_EVENT = "project-start:student-unauthorized";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function readErrorMessage(response: Response): Promise<string> {
  const fallback = response.statusText || `Ошибка ${response.status}`;
  const contentType = response.headers.get("content-type") ?? "";
  let text = "";
  try {
    text = await response.text();
  } catch {
    return fallback;
  }

  if (contentType.includes("application/json")) {
    try {
      const payload = JSON.parse(text) as { detail?: unknown };
      if (typeof payload.detail === "string") return payload.detail;
      if (Array.isArray(payload.detail)) {
        return payload.detail
          .map((item) => {
            if (typeof item === "string") return item;
            if (item && typeof item === "object" && "msg" in item) return String(item.msg);
            return "";
          })
          .filter(Boolean)
          .join("; ") || fallback;
      }
    } catch {
      return fallback;
    }
  }

  return text || fallback;
}

export async function apiRequest<T>(
  path: string,
  options: { method?: string; body?: unknown; auth?: boolean | "admin" } = {},
): Promise<T> {
  const { method = "GET", body, auth = true } = options;

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (auth) {
    const token = auth === "admin" ? getAdminToken() : getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    if (auth === "admin" && response.status === 401) {
      clearAdminToken();
      window.dispatchEvent(new Event(ADMIN_UNAUTHORIZED_EVENT));
    } else if (auth === true && response.status === 401) {
      clearToken();
      window.dispatchEvent(new Event(STUDENT_UNAUTHORIZED_EVENT));
    }
    throw new ApiError(response.status, await readErrorMessage(response));
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
