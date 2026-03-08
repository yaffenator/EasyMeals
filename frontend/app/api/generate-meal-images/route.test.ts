import fs from "fs";
import { spawn } from "child_process";

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

jest.mock("fs", () => ({
  mkdirSync: jest.fn(),
  openSync: jest.fn(() => 99),
  closeSync: jest.fn(),
}));

jest.mock("child_process", () => ({
  spawn: jest.fn(() => ({
    unref: jest.fn(),
  })),
}));

describe("POST /api/generate-meal-images", () => {
  it("starts detached image worker and returns job metadata", async () => {
    const { POST } = await import("./route");
    const request = {
      json: async () => ({ uid: "user_123" }),
    } as unknown as Request;

    const response = await POST(request);
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.uid).toBe("user_123");
    expect(typeof body.jobId).toBe("string");
    expect(typeof body.logPath).toBe("string");

    expect(fs.mkdirSync).toHaveBeenCalled();
    expect(fs.openSync).toHaveBeenCalled();
    expect(fs.closeSync).toHaveBeenCalledWith(99);
    expect(spawn).toHaveBeenCalled();
  });

  it("returns 400 when uid is missing", async () => {
    const { POST } = await import("./route");
    const request = {
      json: async () => ({}),
    } as unknown as Request;

    const response = await POST(request);
    expect(response.status).toBe(400);
  });
});
