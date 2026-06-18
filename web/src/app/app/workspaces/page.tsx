import { Suspense } from "react";
import WorkspacesDashboardPage from "@/refresh-pages/WorkspacesDashboardPage";
import * as AppLayouts from "@/layouts/app-layouts";

export default function Page() {
  return (
    <AppLayouts.Root>
      <Suspense fallback={null}>
        <WorkspacesDashboardPage />
      </Suspense>
    </AppLayouts.Root>
  );
}
