import { config } from "../config/env";
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}
export async function request<T>(
  path: string,
  token: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(
      /^https?:\/\//.test(path) ? path : config.api + path,
      {
        ...options,
        headers,
        signal: options.signal || AbortSignal.timeout(310000),
      },
    );
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    throw new ApiError(
      "Could not reach the server. Check your connection and try again.",
      0,
    );
  }
  const body = await response.json().catch(() => null);
  if (!response.ok)
    throw new ApiError(
      body?.error?.message || `Request failed (${response.status})`,
      response.status,
    );
  if (!body || !("data" in body))
    throw new ApiError("Unexpected server response", response.status);
  return body.data as T;
}
