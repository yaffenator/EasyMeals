import { NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

export const runtime = "nodejs";

interface TriggerPayload {
  uid?: string;
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as TriggerPayload;
    const uid = body?.uid;

    if (!uid || typeof uid !== "string") {
      return NextResponse.json({ error: "uid is required" }, { status: 400 });
    }

    const frontendRoot = process.cwd();
    const repoRoot = path.resolve(frontendRoot, "..");
    const scriptPath = path.join(repoRoot, "backend", "generate_meal_images.py");

    const pythonBin = process.env.PYTHON_BIN || (process.platform === "win32" ? "python" : "python3");

    const args = [
      scriptPath,
      "--user-id",
      uid,
      "--retry-failed",
      "--passes",
      "3",
      "--attempts-per-meal",
      "2",
      "--max-attempts",
      "8",
    ];

    const child = spawn(pythonBin, args, {
      cwd: repoRoot,
      detached: true,
      stdio: "ignore",
      env: process.env,
    });

    child.unref();

    return NextResponse.json({
      ok: true,
      message: "Image generation job started",
      uid,
    });
  } catch (error) {
    console.error("Failed to start image generation job", error);
    return NextResponse.json({ error: "Failed to start image generation" }, { status: 500 });
  }
}
