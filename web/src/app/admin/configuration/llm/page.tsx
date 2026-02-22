"use client";

import { AdminPageTitle } from "@/components/admin/Title";
import { LLMConfiguration } from "./LLMConfiguration";
import { SvgCpu } from "@opal/icons";
export default function Page() {
  return (
    <>
      <AdminPageTitle
        title="Language Models"
        icon={SvgCpu}
        description="Configure LLM providers that power your AI agents and features."
      />

      <LLMConfiguration />
    </>
  );
}
