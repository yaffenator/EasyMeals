import { NextResponse } from "next/server";

export async function POST(request: Request) {
  void request;
  return NextResponse.json(
    {
      detail:
        "Deprecated endpoint. Meal details now come from backend plan payload via /api/plan/generate and /api/plan/latest.",
    },
    { status: 410 },
  );
}
