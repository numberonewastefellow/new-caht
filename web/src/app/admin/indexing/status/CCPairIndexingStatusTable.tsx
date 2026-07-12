import React from "react";
import { Badge } from "@/components/ui/badge";
import { CCPairStatus } from "@/components/Status";
import { timeAgo } from "@/lib/time";
import {
  ValidSources,
  ConnectorIndexingStatusLiteResponse,
  SourceSummary,
  ConnectorIndexingStatusLite,
  FederatedConnectorStatus,
} from "@/lib/types";
import type { Route } from "next";
import { useRouter } from "next/navigation";
import {
  FiChevronDown,
  FiChevronRight,
  FiLock,
  FiUnlock,
  FiRefreshCw,
} from "react-icons/fi";
import SimpleTooltip from "@/refresh-components/SimpleTooltip";
import { SourceIcon } from "@/components/SourceIcon";
import { getSourceDisplayName } from "@/lib/sources";
import { ConnectorCredentialPairStatus } from "../../connector/[ccPairId]/types";
import { PageSelector } from "@/components/PageSelector";
import { ConnectorStaggeredSkeleton } from "./ConnectorRowSkeleton";
import { Button } from "@opal/components";
import { SvgSettings } from "@opal/icons";
import Text from "@/refresh-components/texts/Text";
import { cn } from "@/lib/utils";
import { getSourceColor } from "@/lib/sourceColors";

// Helper to handle navigation with cmd/ctrl+click support
// NOTE: using this rather than Next/Link (or similar) since shadcn
// table row components must be direct descendants of the table component
// and putting the <Link> inside the <TableRow> would causes some parts of the
// row to not navigate as expected.
function navigateWithModifier(
  e: React.MouseEvent,
  url: string,
  router: ReturnType<typeof useRouter>
) {
  if (e.metaKey || e.ctrlKey) {
    window.open(url, "_blank");
  } else {
    router.push(url as Route);
  }
}

function isFederatedConnectorStatus(
  status: ConnectorIndexingStatusLite | FederatedConnectorStatus
) {
  return status.name?.toLowerCase().includes("federated");
}

const NUMBER_OF_ROWS_PER_PAGE = 10;

/** Metric pill shown in SummaryRow */
function MetricPill({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: boolean;
}) {
  return (
    <div className="flex flex-col items-center px-3 lg:px-4">
      <Text as="span" secondaryBody text03 className="text-[11px] uppercase tracking-wide mb-0.5">
        {label}
      </Text>
      <Text
        as="span"
        className={cn(
          "text-lg font-semibold tabular-nums",
          accent ? "text-text-05" : "text-text-04"
        )}
      >
        {value}
      </Text>
    </div>
  );
}

function SummaryRow({
  source,
  summary,
  isOpen,
  onToggle,
}: {
  source: ValidSources;
  summary: SourceSummary;
  isOpen: boolean;
  onToggle: () => void;
}) {
  const colors = getSourceColor(source);

  const activeRatio = summary.total_connectors > 0
    ? summary.active_connectors / summary.total_connectors
    : 0;

  return (
    <div
      onClick={onToggle}
      className={cn(
        "group flex items-center justify-between gap-4 rounded-12 border cursor-pointer transition-all overflow-hidden virtualai-card-hover",
        isOpen
          ? "border-border-02 shadow-sm"
          : "border-border-01 hover:border-border-02 hover:shadow-sm"
      )}
    >
      {/* Colored accent bar on the left */}
      <div className="flex items-center gap-0 flex-1 min-w-0">
        <div className={cn("w-1 self-stretch flex-shrink-0 rounded-l-12", colors.solid)} />

        <div className="flex items-center gap-3 px-4 py-4 flex-1 min-w-0">
          {/* Chevron */}
          <div className="flex-shrink-0 text-text-03 group-hover:text-text-04 transition-colors">
            {isOpen ? (
              <FiChevronDown size={16} />
            ) : (
              <FiChevronRight size={16} />
            )}
          </div>

          {/* Color-tinted icon badge */}
          <div className={cn(
            "w-10 h-10 rounded-08 flex items-center justify-center flex-shrink-0",
            colors.bg
          )}>
            <SourceIcon iconSize={22} sourceType={source} />
          </div>

          {/* Source name */}
          <Text as="span" className="text-text-05 font-semibold text-base truncate">
            {getSourceDisplayName(source)}
          </Text>
        </div>
      </div>

      {/* Right: metrics */}
      <div className="flex items-center gap-1 flex-shrink-0 pr-4">
        <MetricPill label="Total" value={summary.total_connectors} accent />
        <div className="w-px h-8 bg-border-01" />
        <MetricPill
          label="Active"
          value={`${summary.active_connectors}/${summary.total_connectors}`}
        />
        <div className="w-px h-8 bg-border-01" />
        <MetricPill
          label="Public"
          value={`${summary.public_connectors}/${summary.total_connectors}`}
        />
        <div className="w-px h-8 bg-border-01" />
        <MetricPill
          label="Docs"
          value={summary.total_docs_indexed.toLocaleString()}
          accent
        />

        {/* Health indicator dot */}
        <div className="ml-3 flex-shrink-0">
          <SimpleTooltip
            tooltip={
              activeRatio >= 1
                ? "All connectors active"
                : activeRatio > 0
                  ? "Some connectors inactive"
                  : "No active connectors"
            }
          >
            <div
              className={cn(
                "w-2.5 h-2.5 rounded-full ring-2",
                activeRatio >= 1
                  ? "bg-status-success-05 ring-status-success-05/20"
                  : activeRatio > 0
                    ? "bg-status-warning-05 ring-status-warning-05/20"
                    : "bg-status-error-05 ring-status-error-05/20"
              )}
            />
          </SimpleTooltip>
        </div>
      </div>
    </div>
  );
}

/** Column header row for expanded source */
function ColumnHeaders() {
  return (
    <div
      className={cn(
        "grid items-center px-5 py-2.5 text-[11px] uppercase tracking-wider text-text-03 font-medium border-b border-border-01 bg-background-neutral-01/50",
        "grid-cols-[1fr_120px_140px_160px_100px_48px]"
      )}
    >
      <span>Name</span>
      <span>Last Indexed</span>
      <span>Status</span>
      <span>Access</span>
      <span>Docs</span>
      <span />
    </div>
  );
}

function ConnectorRow({
  ccPairsIndexingStatus,
  invisible,
  isEditable,
}: {
  ccPairsIndexingStatus: ConnectorIndexingStatusLite;
  invisible?: boolean;
  isEditable: boolean;
}) {
  const router = useRouter();

  const connectorUrl = `/admin/connector/${ccPairsIndexingStatus.cc_pair_id}`;

  const handleRowClick = (e: React.MouseEvent) => {
    navigateWithModifier(e, connectorUrl, router);
  };

  if (invisible) return null;

  return (
    <div
      className={cn(
        "grid items-center px-5 py-3 border-b border-border-01 cursor-pointer transition-colors virtualai-card-hover",
        "group",
        "grid-cols-[1fr_120px_140px_160px_100px_48px]"
      )}
      onClick={handleRowClick}
    >
      <div className="min-w-0">
        <Text as="p" secondaryBody className="text-text-05 truncate">
          {ccPairsIndexingStatus.name}
        </Text>
      </div>
      <div>
        <Text as="span" secondaryBody text03>
          {timeAgo(ccPairsIndexingStatus?.last_success) || "-"}
        </Text>
      </div>
      <div>
        <CCPairStatus
          ccPairStatus={
            ccPairsIndexingStatus.last_finished_status !== null
              ? ccPairsIndexingStatus.cc_pair_status
              : ccPairsIndexingStatus.last_status == "not_started"
                ? ConnectorCredentialPairStatus.SCHEDULED
                : ConnectorCredentialPairStatus.INITIAL_INDEXING
          }
          inRepeatedErrorState={ccPairsIndexingStatus.in_repeated_error_state}
          lastIndexAttemptStatus={ccPairsIndexingStatus.last_status}
        />
      </div>
      <div>
        {ccPairsIndexingStatus.access_type === "public" ? (
          <Badge variant={isEditable ? "success" : "default"} icon={FiUnlock}>
            Public
          </Badge>
        ) : ccPairsIndexingStatus.access_type === "sync" ? (
          <Badge
            variant={isEditable ? "auto-sync" : "default"}
            icon={FiRefreshCw}
          >
            Sync
          </Badge>
        ) : (
          <Badge variant={isEditable ? "private" : "default"} icon={FiLock}>
            Private
          </Badge>
        )}
      </div>
      <div>
        <Text as="span" secondaryBody className="text-text-04 tabular-nums">
          {ccPairsIndexingStatus.docs_indexed.toLocaleString()}
        </Text>
      </div>
      <div className="flex justify-center">
        {isEditable && (
          <SimpleTooltip tooltip="Manage Connector">
            <Button icon={SvgSettings} prominence="tertiary" />
          </SimpleTooltip>
        )}
      </div>
    </div>
  );
}

function FederatedConnectorRow({
  federatedConnector,
  invisible,
}: {
  federatedConnector: FederatedConnectorStatus;
  invisible?: boolean;
}) {
  const router = useRouter();

  const federatedUrl = `/admin/federated/${federatedConnector.id}`;

  const handleRowClick = (e: React.MouseEvent) => {
    navigateWithModifier(e, federatedUrl, router);
  };

  if (invisible) return null;

  return (
    <div
      className={cn(
        "grid items-center px-5 py-3 border-b border-border-01 cursor-pointer transition-colors virtualai-card-hover",
        "group",
        "grid-cols-[1fr_120px_140px_160px_100px_48px]"
      )}
      onClick={handleRowClick}
    >
      <div className="min-w-0">
        <Text as="p" secondaryBody className="text-text-05 truncate">
          {federatedConnector.name}
        </Text>
      </div>
      <div>
        <Text as="span" secondaryBody text03>
          N/A
        </Text>
      </div>
      <div>
        <Badge variant="success">Indexed</Badge>
      </div>
      <div>
        <Badge variant="secondary" icon={FiRefreshCw}>
          Federated
        </Badge>
      </div>
      <div>
        <Text as="span" secondaryBody text03>
          N/A
        </Text>
      </div>
      <div className="flex justify-center">
        <Button
          icon={SvgSettings}
          prominence="tertiary"
          onClick={(e: React.MouseEvent) => {
            e.stopPropagation();
            navigateWithModifier(e, federatedUrl, router);
          }}
          tooltip="Manage Federated Connector"
        />
      </div>
    </div>
  );
}

export function CCPairIndexingStatusTable({
  ccPairsIndexingStatuses,
  connectorsToggled,
  toggleSource,
  onPageChange,
  sourceLoadingStates = {} as Record<ValidSources, boolean>,
}: {
  ccPairsIndexingStatuses: ConnectorIndexingStatusLiteResponse[];
  connectorsToggled: Record<ValidSources, boolean>;
  toggleSource: (source: ValidSources, toggled?: boolean | null) => void;
  onPageChange: (source: ValidSources, newPage: number) => void;
  sourceLoadingStates?: Record<ValidSources, boolean>;
}) {
  return (
    <div className="flex flex-col gap-3 mt-2">
      {ccPairsIndexingStatuses.map((ccPairStatus) => {
        const colors = getSourceColor(ccPairStatus.source);

        return (
          <div key={ccPairStatus.source}>
            {/* Source group header card */}
            <SummaryRow
              source={ccPairStatus.source}
              summary={ccPairStatus.summary}
              isOpen={connectorsToggled[ccPairStatus.source] || false}
              onToggle={() => toggleSource(ccPairStatus.source)}
            />

            {/* Expanded connector list */}
            {connectorsToggled[ccPairStatus.source] && (
              <div className={cn(
                "ml-6 mt-1 border rounded-08 overflow-hidden bg-background-tint-00 virtualai-accent-border-top",
                colors.border
              )}>
                {sourceLoadingStates[ccPairStatus.source] ? (
                  <div className="py-4">
                    <ConnectorStaggeredSkeleton rowCount={4} standalone={true} />
                  </div>
                ) : (
                  <>
                    {/* Column headers */}
                    <ColumnHeaders />

                    {/* Connector rows */}
                    {ccPairStatus.indexing_statuses.map((indexingStatus) => {
                      if (isFederatedConnectorStatus(indexingStatus)) {
                        const status =
                          indexingStatus as FederatedConnectorStatus;
                        return (
                          <FederatedConnectorRow
                            key={status.id}
                            federatedConnector={status}
                          />
                        );
                      } else {
                        const status =
                          indexingStatus as ConnectorIndexingStatusLite;
                        return (
                          <ConnectorRow
                            key={status.cc_pair_id}
                            ccPairsIndexingStatus={status}
                            isEditable={status.is_editable}
                          />
                        );
                      }
                    })}

                    {/* "All caught up" message when fewer rows than page size with pagination */}
                    {ccPairStatus.indexing_statuses.length <
                      NUMBER_OF_ROWS_PER_PAGE &&
                      ccPairStatus.total_pages > 1 && (
                        <div className="px-5 py-4 text-center">
                          <Text as="span" secondaryBody text03 className="italic">
                            All caught up! No more connectors to show
                          </Text>
                        </div>
                      )}
                  </>
                )}

                {/* Pagination */}
                {ccPairStatus.total_pages > 1 && (
                  <div className="flex justify-center py-3 border-t border-border-01">
                    <PageSelector
                      currentPage={ccPairStatus.current_page}
                      totalPages={ccPairStatus.total_pages}
                      onPageChange={(newPage) =>
                        onPageChange(ccPairStatus.source, newPage)
                      }
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
