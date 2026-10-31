"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";
import ErrorPageLayout from "@/components/errorPages/ErrorPageLayout";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";

// Catches render errors in any page, keeping the root layout (theme, providers).
// Errors in the root layout itself go to global-error.tsx instead.
export default function PageError({
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
    <ErrorPageLayout>
      <Text as="p" headingH2>
        This page hit an error
      </Text>

      <Text as="p" text03>
        {error.message}
      </Text>

      {error.digest && (
        <Text as="p" text03>
          Reference: {error.digest}
        </Text>
      )}

      {/* A full reload rather than reset(): it also recovers from stale JS chunks
          left in an open tab after a new web image is deployed. */}
      <div>
        <Button primary onClick={() => window.location.reload()}>
          Reload page
        </Button>
      </div>
    </ErrorPageLayout>
  );
}
