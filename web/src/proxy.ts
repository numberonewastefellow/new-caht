import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { AuthType, SERVER_SIDE_ONLY__AUTH_TYPE } from "./lib/constants";

// Authentication cookie names (matches backend constants)
const FASTAPI_USERS_AUTH_COOKIE_NAME = "fastapiusersauth";
const ANONYMOUS_USER_COOKIE_NAME = "onyx_anonymous_user";

// Protected route prefixes (require authentication)
const PROTECTED_ROUTES = ["/app", "/admin", "/assistants", "/connector"];

// Public route prefixes (no authentication required)
const PUBLIC_ROUTES = ["/auth", "/anonymous", "/_next", "/api"];

// NOTE: have to have the "/:path*" here since NextJS doesn't allow any real JS to
// be run before the config is defined e.g. if we try and do a .map it will complain
// NOTE: the former Enterprise-Edition entries (/admin/groups, /admin/theme,
// /admin/performance/*, /admin/standard-answer, /assistants/stats, /admin/billing) are
// gone. They existed only to feed the `/ee` rewrite below, and every one of them is
// already covered by the "/admin/:path*" / "/assistants/:path*" prefixes above.
export const config = {
  matcher: [
    // Auth-protected routes (for middleware auth check)
    "/app/:path*",
    "/admin/:path*",
    "/assistants/:path*",
    "/connector/:path*",
  ],
};

export async function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // Auth Check: Fast-fail at edge if no cookie (defense in depth)
  // Note: Layouts still do full verification (token validity, roles, etc.)
  const isProtectedRoute = PROTECTED_ROUTES.some((route) =>
    pathname.startsWith(route)
  );
  const isPublicRoute = PUBLIC_ROUTES.some((route) =>
    pathname.startsWith(route)
  );

  if (isProtectedRoute && !isPublicRoute) {
    const authCookie = request.cookies.get(FASTAPI_USERS_AUTH_COOKIE_NAME);
    const anonymousCookie = request.cookies.get(ANONYMOUS_USER_COOKIE_NAME);

    // Allow access if user has either a regular auth cookie or anonymous user cookie
    if (!authCookie && !anonymousCookie) {
      const loginUrl = new URL("/auth/login", request.url);
      // Preserve full URL including query params and hash for deep linking
      const fullPath = pathname + request.nextUrl.search + request.nextUrl.hash;
      loginUrl.searchParams.set("next", fullPath);
      return NextResponse.redirect(loginUrl);
    }
  }

  // The EE rewrite (/admin/groups -> /ee/admin/groups, etc.) is gone: those pages now
  // live at their canonical /admin/* paths, so there is nothing to rewrite. Old /ee/*
  // bookmarks are handled by a permanent redirect in next.config.js.
  return NextResponse.next();
}
