import { validateInternalRedirect } from "@/lib/auth/redirectValidation";
import { getDomain } from "@/lib/redirectSS";
import { buildUrl } from "@/lib/utilsSS";
import { NextRequest, NextResponse } from "next/server";

// have to use this so we don't hit the redirect URL with a `POST` request
const SEE_OTHER_REDIRECT_STATUS = 303;

async function handleSamlCallback(
  request: NextRequest,
  method: "GET" | "POST"
) {
  // Wrapper around the FastAPI endpoint /sso/saml/acs (WS-C clean-room SAML),
  // which adds back a redirect to the main app. This web route path stays
  // /auth/saml/callback — it is the public, IdP-facing ACS URL.
  const url = new URL(buildUrl("/sso/saml/acs"));
  url.search = request.nextUrl.search;

  const fetchOptions: RequestInit = {
    method,
    headers: {
      "X-Forwarded-Host":
        request.headers.get("X-Forwarded-Host") ||
        request.headers.get("host") ||
        "",
      "X-Forwarded-Port":
        request.headers.get("X-Forwarded-Port") ||
        new URL(request.url).port ||
        "",
    },
  };

  let relayState: string | null = null;

  // For POST requests, include form data
  if (method === "POST") {
    const formData = await request.formData();
    const relayStateValue = formData.get("RelayState");
    relayState = typeof relayStateValue === "string" ? relayStateValue : null;
    fetchOptions.body = formData;
  }

  // OneLogin python toolkit only supports HTTP-POST binding for SAMLResponse.
  // If the IdP returned SAMLResponse via query parameters (GET), convert to POST.
  if (method === "GET") {
    const samlResponse = request.nextUrl.searchParams.get("SAMLResponse");
    relayState = request.nextUrl.searchParams.get("RelayState");
    if (samlResponse) {
      const formData = new FormData();
      formData.set("SAMLResponse", samlResponse);
      if (relayState) {
        formData.set("RelayState", relayState);
      }
      // Clear query on backend URL and send as POST with form body
      url.search = "";
      fetchOptions.method = "POST";
      fetchOptions.body = formData;
    }
  }

  const response = await fetch(url.toString(), fetchOptions);
  const setCookieHeader = response.headers.get("set-cookie");

  if (!setCookieHeader) {
    return NextResponse.redirect(
      new URL("/auth/error", getDomain(request)),
      SEE_OTHER_REDIRECT_STATUS
    );
  }

  const validatedRelayState = validateInternalRedirect(relayState);
  const redirectDestination = validatedRelayState ?? "/";

  const redirectResponse = NextResponse.redirect(
    new URL(redirectDestination, getDomain(request)),
    SEE_OTHER_REDIRECT_STATUS
  );
  redirectResponse.headers.set("set-cookie", setCookieHeader);
  return redirectResponse;
}

export const GET = async (request: NextRequest) => {
  return handleSamlCallback(request, "GET");
};

export const POST = async (request: NextRequest) => {
  return handleSamlCallback(request, "POST");
};
