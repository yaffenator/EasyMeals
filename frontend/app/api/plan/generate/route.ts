import { NextResponse } from "next/server";

import {
  BackendProxyError,
  extractForwardHeaders,
  forwardToBackend,
  passthroughResponse,
  readBearerHeader,
} from "@/app/lib/backendClient";

export const maxDuration = 120;

export async function POST(request: Request) {
  try {
    const authorization = readBearerHeader(request.headers);
    if (!authorization) {
      return NextResponse.json({ detail: "Missing Authorization bearer token" }, { status: 401 });
    }

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
