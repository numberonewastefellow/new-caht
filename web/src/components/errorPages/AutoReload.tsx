"use client";

import { useEffect, useState } from "react";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import {
  AUTO_RELOAD_INTERVAL_MS,
  shouldAutoReload,
} from "@/lib/autoReloadWindow";

export default function AutoReload() {
  const [retrying, setRetrying] = useState(true);

  useEffect(() => {
    if (!shouldAutoReload(window.sessionStorage, Date.now())) {
      setRetrying(false);
      return;
    }
    const timer = setTimeout(
      () => window.location.reload(),
      AUTO_RELOAD_INTERVAL_MS
    );
    return () => clearTimeout(timer);
  }, []);

  if (retrying) {
    return (
      <Text as="p" text03>
        Retrying automatically…
      </Text>
    );
  }

  return (
    <div>
      <Button primary onClick={() => window.location.reload()}>
        Reload page
      </Button>
    </div>
  );
}
