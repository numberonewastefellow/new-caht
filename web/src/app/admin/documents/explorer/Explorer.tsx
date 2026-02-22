"use client";

import { adminSearch } from "./lib";
import { MagnifyingGlass } from "@phosphor-icons/react";
import { useState, useEffect, useCallback } from "react";
import { OnyxDocument } from "@/lib/search/interfaces";
import { buildDocumentSummaryDisplay } from "@/components/search/DocumentDisplay";
import Checkbox from "@/refresh-components/inputs/Checkbox";
import { updateHiddenStatus } from "../lib";
import { toast } from "@/hooks/useToast";
import { getErrorMsg } from "@/lib/fetchUtils";
import { ScoreSection } from "../ScoreEditor";
import { useRouter } from "next/navigation";
import { useFilters } from "@/lib/hooks";
import { buildFilters } from "@/lib/search/utils";
import { DocumentUpdatedAtBadge } from "@/components/search/DocumentUpdatedAtBadge";
import { DocumentSetSummary } from "@/lib/types";
import { SourceIcon } from "@/components/SourceIcon";
import { Connector } from "@/lib/connectors/connectors";
import { HorizontalFilters } from "@/components/filters/SourceSelector";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import { ThreeDotsLoader } from "@/components/Loading";

const DocumentDisplay = ({
  document,
  refresh,
}: {
  document: OnyxDocument;
  refresh: () => void;
}) => {
  return (
    <div
      key={document.document_id}
      className="text-sm border border-border-01 rounded-12 p-4 bg-background-neutral-00 transition-shadow hover:shadow-sm"
    >
      <div className="flex items-center">
        <a
          className={
            "rounded-08 flex items-center font-semibold text-text-05 " +
            (document.link ? "hover:underline underline-offset-2" : "pointer-events-none")
          }
          href={document.link}
          target="_blank"
          rel="noopener noreferrer"
        >
          <SourceIcon sourceType={document.source_type} iconSize={20} />
          <p className="truncate break-all ml-2 my-auto text-sm">
            {document.semantic_identifier || document.document_id}
          </p>
        </a>
      </div>
      <div className="flex flex-wrap gap-2 mt-2.5 text-xs">
        <div className="px-2 py-1 bg-background-tint-02 rounded-08 flex items-center gap-1.5">
          <span className="text-text-03 font-medium">Relevance:</span>
          <ScoreSection
            documentId={document.document_id}
            initialScore={document.boost}
            refresh={refresh}
            consistentWidth={false}
          />
        </div>
        <div
          onClick={async () => {
            const response = await updateHiddenStatus(
              document.document_id,
              !document.hidden
            );
            if (response.ok) {
              refresh();
            } else {
              toast.error(
                `Failed to update document - ${getErrorMsg(response)}`
              );
            }
          }}
          className="px-2 py-1 bg-background-tint-02 hover:bg-background-tint-03 rounded-08 flex items-center gap-1.5 cursor-pointer select-none transition-colors"
        >
          <span className="my-auto">
            {document.hidden ? (
              <span className="text-error font-medium">Excluded</span>
            ) : (
              <span className="text-text-04 font-medium">Indexed</span>
            )}
          </span>
          <Checkbox checked={!document.hidden} />
        </div>
        {document.updated_at && (
          <DocumentUpdatedAtBadge updatedAt={document.updated_at} />
        )}
      </div>
      <p className="pt-2.5 break-words text-text-03 leading-relaxed">
        {buildDocumentSummaryDisplay(document.match_highlights, document.blurb)}
      </p>
    </div>
  );
};

export function Explorer({
  initialSearchValue,
  connectors,
  documentSets,
}: {
  initialSearchValue: string | undefined;
  connectors: Connector<any>[];
  documentSets: DocumentSetSummary[];
}) {
  const router = useRouter();

  const [query, setQuery] = useState(initialSearchValue || "");
  const [timeoutId, setTimeoutId] = useState<number | null>(null);
  const [results, setResults] = useState<OnyxDocument[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const filterManager = useFilters();

  const onSearch = useCallback(
    async (query: string) => {
      setIsLoading(true);
      try {
        const filters = buildFilters(
          filterManager.selectedSources,
          filterManager.selectedDocumentSets,
          filterManager.timeRange,
          filterManager.selectedTags
        );
        const results = await adminSearch(query, filters);
        if (results.ok) {
          setResults((await results.json()).documents);
        }
      } finally {
        setTimeoutId(null);
        setIsLoading(false);
      }
    },
    [
      filterManager.selectedDocumentSets,
      filterManager.selectedSources,
      filterManager.timeRange,
      filterManager.selectedTags,
    ]
  );

  useEffect(() => {
    if (timeoutId !== null) {
      clearTimeout(timeoutId);
    }
    router.replace(
      `/admin/documents/explorer?query=${encodeURIComponent(query)}`
    );

    const newTimeoutId = window.setTimeout(() => onSearch(query), 300);
    setTimeoutId(newTimeoutId);
  }, [
    query,
    filterManager.selectedDocumentSets,
    filterManager.selectedSources,
    filterManager.timeRange,
  ]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col justify-center gap-3">
        <InputTypeIn
          placeholder="Search knowledge base by title or content..."
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
          }}
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              !event.shiftKey &&
              !(event.nativeEvent as any).isComposing
            ) {
              onSearch(query);
              event.preventDefault();
            }
          }}
          role="textarea"
        />

        <HorizontalFilters
          {...filterManager}
          availableDocumentSets={documentSets}
          existingSources={connectors.map((connector) => connector.source)}
          availableTags={[]}
          toggleFilters={() => {}}
          filtersUntoggled={false}
          tagsOnLeft={true}
        />
      </div>

      {isLoading && (
        <div className="flex justify-center py-8">
          <ThreeDotsLoader />
        </div>
      )}

      {!isLoading && results.length > 0 && (
        <div className="space-y-3">
          {results.map((document) => (
            <DocumentDisplay
              key={document.document_id}
              document={document}
              refresh={() => onSearch(query)}
            />
          ))}
        </div>
      )}

      {!isLoading && query && results.length === 0 && (
        <div className="text-center py-12">
          <MagnifyingGlass className="w-10 h-10 mx-auto mb-3 text-text-02" />
          <p className="text-text-03 text-sm">
            No documents found matching your search.
          </p>
        </div>
      )}
    </div>
  );
}
