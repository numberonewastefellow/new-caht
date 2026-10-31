import { Suspense } from "react";
import WebhookDetailPage from "@/refresh-pages/WebhookDetailPage";
import * as AppLayouts from "@/layouts/app-layouts";

export default async function Page(props: { params: Promise<{ id: string }> }) {
  const { id } = await props.params;
  return (
    <AppLayouts.Root>
      <Suspense fallback={null}>
        <WebhookDetailPage webhookId={Number.parseInt(id, 10)} />
      </Suspense>
    </AppLayouts.Root>
  );
}
