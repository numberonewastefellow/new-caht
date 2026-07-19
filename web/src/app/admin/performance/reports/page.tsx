"use client";

import React, { useState } from "react";
import useSWR from "swr";
import { SvgFileText, SvgDownloadCloud } from "@opal/icons";

import { AdminPageTitle } from "@/components/admin/Title";
import CardSection from "@/components/admin/CardSection";
import Text from "@/refresh-components/texts/Text";
import Button from "@/refresh-components/buttons/Button";
import { ThreeDotsLoader } from "@/components/Loading";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AdminDateRangeSelector,
  DateRange,
} from "@/components/dateRangeSelectors/AdminDateRangeSelector";
import {
  convertDateToEndOfDay,
  convertDateToStartOfDay,
} from "@/components/dateRangeSelectors/dateUtils";
import { errorHandlingFetcher } from "@/lib/fetcher";

import { defaultDateRange, UsageReportSchema } from "../analytics/lib";

function formatPeriod(from: string | null, to: string | null): string {
  if (!from && !to) return "All time";
  const fmt = (v: string | null) =>
    v ? new Date(v).toLocaleDateString() : "…";
  return `${fmt(from)} → ${fmt(to)}`;
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export default function ReportsPage() {
  const [range, setRange] = useState<DateRange>(defaultDateRange());
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const listUrl = "/api/admin/reports/usage";
  const { data, isLoading, mutate } = useSWR<UsageReportSchema[]>(
    listUrl,
    errorHandlingFetcher
  );

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    try {
      const response = await fetch(listUrl, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          period_from: convertDateToStartOfDay(range?.from)?.toISOString() ?? null,
          period_to: convertDateToEndOfDay(range?.to)?.toISOString() ?? null,
        }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "Failed to generate report");
      }
      await mutate();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate report");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div>
      <AdminPageTitle
        icon={SvgFileText}
        title="Reports"
        description="Generate and download usage reports as CSV."
      />

      <CardSection className="mt-4">
        <div className="mb-3">
          <Text mainUiBody>Generate a usage report</Text>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <AdminDateRangeSelector value={range} onValueChange={setRange} />
          <Button main onClick={handleGenerate} disabled={generating}>
            {generating ? "Generating…" : "Generate report"}
          </Button>
        </div>
        {error && (
          <div className="mt-2">
            <Text secondaryBody className="text-status-error-05">
              {error}
            </Text>
          </div>
        )}
      </CardSection>

      <CardSection className="mt-4">
        <div className="mb-3">
          <Text mainUiBody>Generated reports</Text>
        </div>
        {isLoading ? (
          <ThreeDotsLoader />
        ) : !data || data.length === 0 ? (
          <Text secondaryBody text03>
            No reports generated yet.
          </Text>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Report</TableHead>
                  <TableHead>Requested by</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Download</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((report) => (
                  <TableRow key={report.id}>
                    <TableCell className="max-w-[20rem] truncate">
                      {report.report_name}
                    </TableCell>
                    <TableCell>{report.requestor_email || "—"}</TableCell>
                    <TableCell>
                      {formatPeriod(report.period_from, report.period_to)}
                    </TableCell>
                    <TableCell>{formatTimestamp(report.created_at)}</TableCell>
                    <TableCell>
                      <Button
                        internal
                        leftIcon={SvgDownloadCloud}
                        onClick={() =>
                          window.location.assign(
                            `/api/admin/reports/usage/${report.id}/download`
                          )
                        }
                      >
                        CSV
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardSection>
    </div>
  );
}
