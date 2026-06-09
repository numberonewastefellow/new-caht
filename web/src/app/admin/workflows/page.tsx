import { Suspense } from "react";
import VersionedPage from "@/refresh-components/VersionedPage";
import WorkflowListPage from "@/refresh-pages/WorkflowListPage";
import WorkflowListPageLegacy from "@/refresh-pages/WorkflowListPageLegacy";

// Dual-version page (web-only backward-compat): renders the new "Agentic AI"
// design by default, with an easy switch to the legacy list. Default is
// governed by the DEFAULT_UI_VERSION env var; users can override per-browser
// via the header toggle or ?legacy=1. See AGENTIC_AI_REBRAND_PLAN.md.
//
// Suspense boundary: VersionedPage -> usePageVersion uses useSearchParams(),
// which Next requires to be wrapped in Suspense.
export default function Page() {
  return (
    <Suspense fallback={null}>
      <VersionedPage
        versionKey="agentic-ai"
        current={<WorkflowListPage />}
        legacy={<WorkflowListPageLegacy />}
      />
    </Suspense>
  );
}
