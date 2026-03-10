import { NextResponse } from "next/server";

import { getBackendBaseUrl } from "@/app/lib/backendClient";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const userId = searchParams.get("userId")?.trim();
    const token = searchParams.get("token")?.trim();

    if (!userId) {
      return NextResponse.json({ detail: "userId is required" }, { status: 400 });
    }
    if (!token) {
      return NextResponse.json({ detail: "token is required" }, { status: 400 });
    }

    const backendUrl = `${getBackendBaseUrl()}/api/generate-plan/progress/${encodeURIComponent(userId)}?token=${encodeURIComponent(token)}`;
    const backendResponse = await fetch(backendUrl, {
      method: "GET",
      cache: "no-store",
    });

    if (!backendResponse.ok || !backendResponse.body) {
      const text = await backendResponse.text();
      const detail = text || "Failed to stream progress from backend";
      return NextResponse.json({ detail }, { status: backendResponse.status || 502 });
    }

    return new Response(backendResponse.body, {
      status: backendResponse.status,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch (error) {
    console.error("Failed to proxy progress stream", error);
    return NextResponse.json({ detail: "Failed to proxy progress stream" }, { status: 500 });
  }
}
