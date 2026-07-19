"use client";

import React, { useMemo, useState } from "react";
import useSWR from "swr";
import { SvgServer, SvgDownloadCloud } from "@opal/icons";

import { AdminPageTitle } from "@/components/admin/Title";
import CardSection from "@/components/admin/CardSection";
import Text from "@/refresh-components/texts/Text";
import Button from "@/refresh-components/buttons/Button";
import Modal from "@/refresh-components/Modal";
import { Badge } from "@/components/ui/badge";
import { ThreeDotsLoader } from "@/components/Loading";
import { PageSelector } from "@/components/PageSelector";
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
import { errorHandlingFetcher } from "@/lib/fetcher";
import { buildApiPath } from "@/lib/urlBuilder";

import {
  ChatSessionDetail,
  ChatSessionSummary,
  defaultDateRange,
  PaginatedSessions,
  rangeParams,
} from "../analytics/lib";

const PAGE_SIZE = 10;

type FeedbackFilter = "like" | "dislike" | "mixed" | undefined;

const FEEDBACK_FILTERS: { label: string; value: FeedbackFilter }[] = [
  { label: "All", value: undefined },
  { label: "Liked", value: "like" },
  { label: "Disliked", value: "dislike" },
  { label: "Mixed", value: "mixed" },
];

function FeedbackBadge({ feedback }: { feedback: ChatSessionSummary["feedback"] }) {
  if (!feedback) return <span className="text-text-03">—</span>;
  const variant =
    feedback === "like"
      ? "success"
      : feedback === "dislike"
        ? "destructive"
        : "outline";
  return <Badge variant={variant}>{feedback}</Badge>;
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function SessionDetailModal({
  sessionId,
  onClose,
}: {
  sessionId: string;
  onClose: () => void;
}) {
  const { data, isLoading } = useSWR<ChatSessionDetail>(
    `/api/admin/query-history/sessions/${sessionId}`,
    errorHandlingFetcher
  );

  return (
    <Modal open onOpenChange={onClose}>
      <Modal.Content width="lg" height="lg">
        <Modal.Header
          icon={SvgServer}
          title={data?.name || "Chat session"}
          onClose={onClose}
        />
        <Modal.Body>
          {isLoading || !data ? (
            <ThreeDotsLoader />
          ) : (
            <div className="flex flex-col gap-4">
              <div className="flex flex-wrap gap-4">
                <Text secondaryBody text03>
                  {data.user_email || "Unknown user"}
                </Text>
                {data.agent_name && (
                  <Text secondaryBody text03>
                    Agent: {data.agent_name}
                  </Text>
                )}
                <Text secondaryBody text03>
                  {formatTimestamp(data.time_created)}
                </Text>
              </div>
              <div className="flex flex-col gap-3">
                {data.messages.map((m) => (
                  <div
                    key={m.id}
                    className="rounded-08 border border-border p-3 bg-background-neutral-01"
                  >
                    <div className="mb-1 flex items-center gap-2">
                      <Text secondaryBody text03>
                        {m.message_type}
                      </Text>
                      {m.feedback && <FeedbackBadge feedback={m.feedback} />}
                    </div>
                    <Text mainContentBody className="whitespace-pre-wrap">
                      {m.message}
                    </Text>
                    {m.feedback_text && (
                      <div className="mt-2">
                        <Text secondaryBody text03>
                          Feedback: {m.feedback_text}
                        </Text>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}

export default function QueryLogPage() {
  const [range, setRange] = useState<DateRange>(defaultDateRange());
  const [feedback, setFeedback] = useState<FeedbackFilter>(undefined);
  const [page, setPage] = useState(1); // 1-indexed for PageSelector
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const params = rangeParams(range);
  const listUrl = buildApiPath("/api/admin/query-history/sessions", {
    page_num: String(page - 1),
    page_size: String(PAGE_SIZE),
    feedback_type: feedback,
    start_time: params.start,
    end_time: params.end,
  });
  const { data, isLoading } = useSWR<PaginatedSessions>(
    listUrl,
    errorHandlingFetcher
  );

  const exportUrl = useMemo(
    () =>
      buildApiPath("/api/admin/query-history/export", {
        start_time: params.start,
        end_time: params.end,
      }),
    [params.start, params.end]
  );

  const totalPages = data ? Math.max(1, Math.ceil(data.total_items / PAGE_SIZE)) : 1;

  return (
    <div>
      <AdminPageTitle
        icon={SvgServer}
        title="Query Logs"
        description="Browse and export past chat sessions across the workspace."
        farRightElement={
          <AdminDateRangeSelector value={range} onValueChange={setRange} />
        }
      />

      <div className="flex flex-wrap items-center justify-between gap-3 mt-4">
        <div className="flex flex-wrap gap-2">
          {FEEDBACK_FILTERS.map((f) => (
            <Button
              key={f.label}
              main={feedback === f.value}
              secondary={feedback !== f.value}
              onClick={() => {
                setFeedback(f.value);
                setPage(1);
              }}
            >
              {f.label}
            </Button>
          ))}
        </div>
        <Button
          leftIcon={SvgDownloadCloud}
          secondary
          onClick={() => window.location.assign(exportUrl)}
        >
          Export CSV
        </Button>
      </div>

      <CardSection className="mt-4">
        {isLoading ? (
          <ThreeDotsLoader />
        ) : !data || data.items.length === 0 ? (
          <Text secondaryBody text03>
            No chat sessions found for the selected filters.
          </Text>
        ) : (
          <>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>User query</TableHead>
                    <TableHead>AI response</TableHead>
                    <TableHead>Feedback</TableHead>
                    <TableHead>Member</TableHead>
                    <TableHead>Agent</TableHead>
                    <TableHead>Messages</TableHead>
                    <TableHead>Timestamp</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((session) => (
                    <TableRow
                      key={session.id}
                      className="cursor-pointer"
                      onClick={() => setSelectedId(session.id)}
                    >
                      <TableCell className="max-w-[16rem] truncate">
                        {session.first_user_message || "—"}
                      </TableCell>
                      <TableCell className="max-w-[16rem] truncate">
                        {session.first_ai_message || "—"}
                      </TableCell>
                      <TableCell>
                        <FeedbackBadge feedback={session.feedback} />
                      </TableCell>
                      <TableCell>{session.user_email || "—"}</TableCell>
                      <TableCell>{session.agent_name || "—"}</TableCell>
                      <TableCell>{session.message_count}</TableCell>
                      <TableCell>{formatTimestamp(session.time_created)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <div className="mt-4 flex justify-center">
              <PageSelector
                currentPage={page}
                totalPages={totalPages}
                onPageChange={setPage}
              />
            </div>
          </>
        )}
      </CardSection>

      {selectedId && (
        <SessionDetailModal
          sessionId={selectedId}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  );
}
