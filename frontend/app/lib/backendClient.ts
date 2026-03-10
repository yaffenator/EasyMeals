import { NextResponse } from "next/server";

const BACKEND_API_URL = "https://easymeals-imyf.onrender.com"
const DEFAULT_BACKEND_API_URL = "http://localhost:8000";
const DEFAULT_TIMEOUT_MS = 180_000;
const MIN_TIMEOUT_MS = 10_000;
const MAX_TIMEOUT_MS = 180_000;


export class BackendProxyError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export function getBackendBaseUrl(): string {
  const raw = BACKEND_API_URL || DEFAULT_BACKEND_API_URL;
  return raw.endsWith("/") ? raw.slice(0, -1) : raw;
}

function clampTimeoutMs(value: number): number {
  if (value < MIN_TIMEOUT_MS) return MIN_TIMEOUT_MS;
  if (value > MAX_TIMEOUT_MS) return MAX_TIMEOUT_MS;
  return value;
}

export function getBackendTimeoutMs(): number {
  const raw = process.env.BACKEND_PROXY_TIMEOUT_MS;
  if (!raw) return DEFAULT_TIMEOUT_MS;
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed)) return DEFAULT_TIMEOUT_MS;
  return clampTimeoutMs(parsed);
}

export function extractForwardHeaders(source: Headers): HeadersInit {
  const headers = new Headers();
  const authorization = source.get("authorization");
  const contentType = source.get("content-type");
  const accept = source.get("accept");

  if (authorization) headers.set("authorization", authorization);
  if (contentType) headers.set("content-type", contentType);
  if (accept) headers.set("accept", accept);

  return headers;
}

export function readBearerHeader(source: Headers): string | null {
  const authorization = source.get("authorization");
  if (!authorization) return null;
  if (!authorization.startsWith("Bearer ")) return null;
  if (!authorization.slice("Bearer ".length).trim()) return null;
  return authorization;
}

export async function forwardToBackend(
  path: string,
  init: RequestInit,
  timeoutMs: number = getBackendTimeoutMs(),
): Promise<Response> {
  const controller = new AbortController();
  const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(`${getBackendBaseUrl()}${path}`, {
      ...init,
      signal: controller.signal,
      cache: "no-store",
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new BackendProxyError("Backend request timed out", 504);
    }
    throw new BackendProxyError("Failed to reach backend service", 502);
  } finally {
    clearTimeout(timeoutHandle);
  }
}

export async function passthroughResponse(response: Response): Promise<NextResponse> {
  const contentType = response.headers.get("content-type") || "application/json";
  const bodyText = await response.text();
  return new NextResponse(bodyText, {
    status: response.status,
    headers: { "content-type": contentType },
  });
}
