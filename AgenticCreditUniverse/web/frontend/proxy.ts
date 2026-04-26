/**
 * Next.js 16 proxy (formerly middleware) — auth gate.
 * Unauthenticated requests outside `/login` and `/api/*` are redirected to `/login`.
 */
import { NextResponse, type NextRequest } from "next/server";

const COOKIE = "creditu_session";

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 공개 경로
  if (pathname === "/login" || pathname.startsWith("/api/")) {
    return NextResponse.next();
  }

  const session = request.cookies.get(COOKIE);
  if (!session?.value) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  // 정적 자원 (_next, favicon, woff2 등) 은 매처에서 제외
  matcher: ["/((?!_next|favicon\\.ico|.*\\.(?:woff2?|ico|png|jpg|svg)$).*)"],
};
