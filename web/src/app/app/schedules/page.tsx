import { Suspense } from "react";
import SchedulesPage from "@/refresh-pages/SchedulesPage";
import * as AppLayouts from "@/layouts/app-layouts";

export default function Page() {
  return (
    <AppLayouts.Root>
      <Suspense fallback={null}>
        <SchedulesPage />
      </Suspense>
    </AppLayouts.Root>
  );
}
