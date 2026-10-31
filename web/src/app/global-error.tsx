"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

// This global error page is necessary to capture errors that occur in the app.
// It replaces the root layout, so its CSS and theme variables aren't available:
// styles are inline and neutral.
export default function GlobalError({
  error,
}: {
  error: Error & { digest?: string };
}) {
  useEffect(() => {
    console.error(error);
    if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
      Sentry.captureException(error);
    }
  }, [error]);

  return (
    <html style={{ colorScheme: "light dark" }}>
      <body
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "1rem",
          minHeight: "100vh",
          margin: 0,
          padding: "1rem",
          textAlign: "center",
          fontFamily: "system-ui, sans-serif",
        }}
      >
        <h1 style={{ margin: 0, fontSize: "1.5rem" }}>Something went wrong</h1>
        <p style={{ margin: 0 }}>{error.message}</p>
        {error.digest && (
          <p style={{ margin: 0 }}>Reference: {error.digest}</p>
        )}
        <button
          onClick={() => window.location.reload()}
          style={{ padding: "0.5rem 1rem", cursor: "pointer" }}
        >
          Reload page
        </button>
      </body>
    </html>
  );
}
