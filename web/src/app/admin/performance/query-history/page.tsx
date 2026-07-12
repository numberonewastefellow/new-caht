"use client";

import { AdminPageTitle } from "@/components/admin/Title";
import { QueryHistoryTable } from "@/app/admin/performance/query-history/QueryHistoryTable";
import { SvgServer } from "@opal/icons";
export default function QueryHistoryPage() {
  return (
    <>
      <AdminPageTitle
        title="Query Logs"
        icon={SvgServer}
        description="Review AI interactions, user feedback, and export conversation data for analysis."
      />

      <QueryHistoryTable />
    </>
  );
}
