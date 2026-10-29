import { NextResponse, type NextRequest } from "next/server";

// Must match SESSION_COOKIE in api/app/deps.py.
const SESSION_COOKIE = "opsboard_session";

/**
 * UX only: skip the flash of an empty app shell when there's clearly no session.
 * Authorization is the API's job; an expired cookie still passes here and the
 * first API call's 401 sends the user to /login.
 */
export function proxy(request: NextRequest) {
  if (request.cookies.has(SESSION_COOKIE)) return NextResponse.next();
  const login = new URL("/login", request.url);
  const next = request.nextUrl.pathname + request.nextUrl.search;
  if (next !== "/") login.searchParams.set("next", next);
  return NextResponse.redirect(login);
}

export const config = {
  // Everything except the login page, the API proxy, and static assets.
  matcher: ["/((?!login|api|_next/static|_next/image|favicon.ico|icon.svg).*)"],
};
