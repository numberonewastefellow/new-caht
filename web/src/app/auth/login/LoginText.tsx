"use client";

import React, { useContext } from "react";
import { SettingsContext } from "@/providers/SettingsProvider";
import Text from "@/refresh-components/texts/Text";

export default function LoginText() {
  const settings = useContext(SettingsContext);
  const appName =
    (settings && settings?.enterpriseSettings?.application_name) || "VertualAI";

  return (
    <div className="w-full flex flex-col gap-1 animate-fadeIn">
      <Text as="p" headingH2 text05>
        Welcome to{" "}
        <span
          className="font-bold"
          style={{
            background:
              "linear-gradient(135deg, #E8449A 0%, #C026D3 35%, #7C3AED 65%, #4338CA 100%)",
            backgroundClip: "text",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          {appName}
        </span>
      </Text>
      <Text as="p" text03 mainUiMuted>
        Sign in to your AI platform for work
      </Text>
    </div>
  );
}
