import { NextResponse } from "next/server";

import {
  BackendProxyError,
  extractForwardHeaders,
  forwardToBackend,
  passthroughResponse,
  readBearerHeader,
} from "@/app/lib/backendClient";

export async function GET(request: Request) {
  try {
    const authorization = readBearerHeader(request.headers);
    if (!authorization) {
      return NextResponse.json({ detail: "Missing Authorization bearer token" }, { status: 401 });
    }

    const url = new URL(request.url);
    const userId = url.searchParams.get("userId");

    if (!userId) {
      return NextResponse.json({ detail: "userId is required" }, { status: 400 });
    }

    const backendResponse = await forwardToBackend(`/api/get-plan/${encodeURIComponent(userId)}`, {
      method: "GET",
      headers: extractForwardHeaders(request.headers),
    });
    return passthroughResponse(backendResponse);
  } catch (error) {
    if (error instanceof BackendProxyError) {
      return NextResponse.json({ detail: error.message }, { status: error.status });
    }
    return NextResponse.json({ detail: "Failed to proxy latest plan request" }, { status: 500 });
  }
}
