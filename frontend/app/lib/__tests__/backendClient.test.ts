jest.mock("next/server", () => ({
  NextResponse: class {
    static json(body: unknown, init?: { status?: number }) {
      return {
        status: init?.status ?? 200,
        json: async () => body,
      };
    }
  },
}));

import { getBackendTimeoutMs } from "../backendClient";

describe("getBackendTimeoutMs", () => {
  const original = process.env.BACKEND_PROXY_TIMEOUT_MS;

  afterEach(() => {
    if (original === undefined) {
      delete process.env.BACKEND_PROXY_TIMEOUT_MS;
    } else {
      process.env.BACKEND_PROXY_TIMEOUT_MS = original;
    }
  });

  it("returns configured value when valid", () => {
    process.env.BACKEND_PROXY_TIMEOUT_MS = "120000";
    expect(getBackendTimeoutMs()).toBe(120000);
  });

  it("falls back to default when invalid", () => {
    process.env.BACKEND_PROXY_TIMEOUT_MS = "abc";
    expect(getBackendTimeoutMs()).toBe(180000);
  });

  it("clamps below minimum", () => {
    process.env.BACKEND_PROXY_TIMEOUT_MS = "5000";
    expect(getBackendTimeoutMs()).toBe(10000);
  });

  it("clamps above maximum", () => {
    process.env.BACKEND_PROXY_TIMEOUT_MS = "999999";
    expect(getBackendTimeoutMs()).toBe(180000);
  });
});
