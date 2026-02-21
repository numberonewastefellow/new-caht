"use client";

import { useTheme } from "next-themes";
import { Button } from "@opal/components";
import { SvgSun, SvgMoon } from "@opal/icons";

export default function ThemeToggleButton() {
  const { theme, setTheme } = useTheme();

  return (
    <Button
      icon={theme === "dark" ? SvgSun : SvgMoon}
      prominence="tertiary"
      size="sm"
      tooltip={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      aria-label="Toggle theme"
    />
  );
}
