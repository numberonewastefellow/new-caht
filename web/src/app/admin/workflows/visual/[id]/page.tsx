"use client";

import { use } from "react";
import WorkflowVisualBuilderPage from "@/refresh-pages/WorkflowVisualBuilderPage";

export default function Page(props: { params: Promise<{ id: string }> }) {
  const { id } = use(props.params);
  const workflowId = parseInt(id, 10);

  if (isNaN(workflowId)) {
    return <div>Invalid workflow ID</div>;
  }

  return <WorkflowVisualBuilderPage workflowId={workflowId} />;
}
