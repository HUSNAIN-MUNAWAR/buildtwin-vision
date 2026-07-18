export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
export const MEDIA_ORIGIN = API.replace(/\/api\/v1$/, "");

export function token(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("buildtwin_token");
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const auth = token();
  if (auth) headers.set("Authorization", `Bearer ${auth}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API}${path}`, { ...init, headers, cache: "no-store" });
  if (response.status === 401 && typeof window !== "undefined") {
    window.localStorage.removeItem("buildtwin_token");
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try { const body = await response.json(); detail = body.detail ?? body.error ?? detail; } catch {}
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function mediaUrl(path?: string | null): string {
  if (!path) return "";
  return path.startsWith("http") ? path : `${MEDIA_ORIGIN}${path}`;
}
