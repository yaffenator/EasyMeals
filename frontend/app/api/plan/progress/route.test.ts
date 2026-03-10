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

jest.mock("@/app/lib/backendClient", () => ({
  getBackendBaseUrl: jest.fn(() => "http://localhost:8000"),
}));

describe("GET /api/plan/progress", () => {
  beforeAll(() => {
    (global as unknown as { Response: typeof Response }).Response = class {
      status: number;
      body: ReadableStream<Uint8Array> | null;
      headers: { get: (key: string) => string | null };
      constructor(body?: BodyInit | null, init?: ResponseInit) {
        this.status = init?.status ?? 200;
        this.body = (body ?? null) as ReadableStream<Uint8Array> | null;
        const headersRecord = (init?.headers ?? {}) as Record<string, string>;
        this.headers = {
          get: (key: string) => headersRecord[key] ?? headersRecord[key.toLowerCase()] ?? null,
        };
      }
    } as unknown as typeof Response;
  });

  it("returns 400 when userId is missing", async () => {
    const { GET } = await import("./route");
    const request = { url: "http://localhost:3000/api/plan/progress?token=t" } as Request;

    const response = await GET(request);
    expect(response.status).toBe(400);
  });

  it("proxies backend SSE stream", async () => {
    global.fetch = jest.fn(async () =>
      ({
        ok: true,
        status: 200,
        body: {} as ReadableStream<Uint8Array>,
      }) as Response,
    ) as jest.Mock;

    const { GET } = await import("./route");
    const request = { url: "http://localhost:3000/api/plan/progress?userId=u1&token=t1" } as Request;

    const response = await GET(request);
    expect(response.status).toBe(200);
    expect(response.headers.get("Content-Type")).toBe("text/event-stream");
  });
});
