"use client";

import { use, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useWorkflow } from "@/hooks/useWorkflows";
import WorkflowEditorPage from "@/refresh-pages/WorkflowEditorPage";

export interface PageProps {
  params: Promise<{ id: string }>;
}

export default function Page(props: PageProps) {
  const router = useRouter();
  const { id } = use(props.params);
  const workflowId = parseInt(id);

  const { workflow, isLoading, refresh } = useWorkflow(
    isNaN(workflowId) ? null : workflowId
  );

  useEffect(() => {
    if (isNaN(workflowId)) {
      router.push("/admin/workflows");
    }
  }, [workflowId, router]);

  useEffect(() => {
    if (!isLoading && !workflow) {
      router.push("/admin/workflows");
    }
  }, [isLoading, workflow, router]);

  if (isLoading || !workflow) return null;

  return <WorkflowEditorPage workflow={workflow} refreshWorkflow={refresh} />;
}
