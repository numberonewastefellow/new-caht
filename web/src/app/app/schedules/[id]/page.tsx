import { Suspense } from "react";
import ScheduleDetailPage from "@/refresh-pages/ScheduleDetailPage";
import * as AppLayouts from "@/layouts/app-layouts";

export default async function Page(props: { params: Promise<{ id: string }> }) {
  const { id } = await props.params;
  return (
    <AppLayouts.Root>
      <Suspense fallback={null}>
        <ScheduleDetailPage scheduleId={Number.parseInt(id, 10)} />
      </Suspense>
    </AppLayouts.Root>
  );
}
