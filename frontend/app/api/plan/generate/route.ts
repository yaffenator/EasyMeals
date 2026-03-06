import { NextResponse } from "next/server";

import {
  BackendProxyError,
  extractForwardHeaders,
  forwardToBackend,
  passthroughResponse,
} from "@/app/lib/backendClient";

export async function POST(request: Request) {
  try {
    const payload = await request.json();
    const backendResponse = await forwardToBackend("/api/generate-plan", {
      method: "POST",
      headers: extractForwardHeaders(request.headers),
      body: JSON.stringify(payload),
    });
    return passthroughResponse(backendResponse);
  } catch (error) {
    if (error instanceof BackendProxyError) {
      return NextResponse.json({ detail: error.message }, { status: error.status });
    }
    return NextResponse.json({ detail: "Invalid request payload" }, { status: 400 });
  }
}
