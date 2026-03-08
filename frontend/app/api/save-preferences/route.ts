import { NextResponse } from "next/server";

export async function POST(request: Request) {
  void request;
  return NextResponse.json(
    {
      detail:
        "Deprecated endpoint. Use POST /api/plan/generate (FastAPI proxy) for full plan generation.",
    },
    { status: 410 },
  );
}
