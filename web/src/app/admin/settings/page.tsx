"use client";

import { AdminPageTitle } from "@/components/admin/Title";
import { SettingsForm } from "@/app/admin/settings/SettingsForm";
import { SvgSettings } from "@opal/icons";

export default function Page() {
  return (
    <>
      <AdminPageTitle
        title="General Settings"
        icon={SvgSettings}
        description="Configure workspace behavior, AI features, and platform-wide preferences."
      />

      <SettingsForm />
    </>
  );
}
