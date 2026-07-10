import { Suspense } from "react";
import WorkflowGalleryPage from "@/refresh-pages/WorkflowGalleryPage";
import * as AppLayouts from "@/layouts/app-layouts";

export default function Page() {
  return (
    <AppLayouts.Root>
      <Suspense fallback={null}>
        <WorkflowGalleryPage />
      </Suspense>
    </AppLayouts.Root>
  );
}
