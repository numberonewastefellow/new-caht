"use client";

import { useState, useMemo, Dispatch, SetStateAction } from "react";
import {
  MinimalOnyxDocument,
  OnyxDocument,
} from "@/lib/search/interfaces";
import { SourceIcon } from "@/components/SourceIcon";
import { WebResultIcon } from "@/components/WebResultIcon";
import { ValidSources } from "@/lib/types";
import { openDocument } from "@/lib/search/utils";
import { buildDocumentSummaryDisplay } from "@/components/search/DocumentDisplay";
import { DocumentUpdatedAtBadge } from "@/components/search/DocumentUpdatedAtBadge";
import { MetadataBadge } from "@/components/MetadataBadge";
import { FiTag } from "react-icons/fi";
import Modal from "@/refresh-components/Modal";
import { SvgBookOpen, SvgChevronDown, SvgExternalLink } from "@opal/icons";
import Text from "@/refresh-components/texts/Text";
import { cn } from "@/lib/utils";

interface CitedSourcesModalProps {
  open: boolean;
  onClose: () => void;
  citedDocuments: OnyxDocument[];
  otherDocuments: OnyxDocument[];
  setPresentingDocument: Dispatch<SetStateAction<MinimalOnyxDocument | null>>;
}

function SourceCard({
  document,
  isExpanded,
  onToggle,
  onOpenDocument,
  index,
}: {
  document: OnyxDocument;
  isExpanded: boolean;
  onToggle: () => void;
  onOpenDocument: () => void;
  index: number;
}) {
  const isInternet =
    document.is_internet || document.source_type === ValidSources.Web;
  const title = document.semantic_identifier || document.document_id;
  const hasMetadata =
    document.updated_at || Object.keys(document.metadata).length > 0;
  const summary = buildDocumentSummaryDisplay(
    document.match_highlights,
    document.blurb
  );

  return (
    <div
      className={cn(
        "border rounded-12 transition-all duration-200 overflow-hidden",
        isExpanded
          ? "border-border-02 shadow-sm virtualai-card-hover"
          : "border-border-01 hover:border-border-02"
      )}
    >
      {/* Header — always visible */}
      <button
        type="button"
        onClick={onToggle}
        className={cn(
          "w-full flex items-center gap-3 px-4 py-3 text-left transition-colors cursor-pointer",
          isExpanded
            ? "bg-background-tint-01"
            : "hover:bg-background-neutral-01/50"
        )}
      >
        {/* Citation number badge */}
        <div
          className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-semibold"
          style={{
            backgroundColor: isExpanded
              ? "var(--virtualai-accent, var(--theme-primary-05))"
              : "var(--background-neutral-02)",
            color: isExpanded
              ? "white"
              : "var(--text-03)",
          }}
        >
          {index + 1}
        </div>

        {/* Source icon */}
        <div className="flex-shrink-0">
          {isInternet ? (
            <WebResultIcon url={document.link} size={18} />
          ) : (
            <SourceIcon sourceType={document.source_type} iconSize={18} />
          )}
        </div>

        {/* Title */}
        <div className="flex-1 min-w-0">
          <Text as="p" secondaryBody className="text-text-05 truncate font-medium">
            {title}
          </Text>
          {!isExpanded && document.updated_at && (
            <Text as="p" className="text-[11px] text-text-03 mt-0.5">
              {new Date(document.updated_at).toLocaleDateString()}
            </Text>
          )}
        </div>

        {/* Expand/collapse chevron */}
        <SvgChevronDown
          className={cn(
            "w-4 h-4 text-text-03 flex-shrink-0 transition-transform duration-200",
            isExpanded && "rotate-180"
          )}
        />
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-border-01">
          {/* Metadata badges */}
          {hasMetadata && (
            <div className="flex items-center gap-1 flex-wrap mt-3 mb-2">
              {document.updated_at && (
                <DocumentUpdatedAtBadge updatedAt={document.updated_at} />
              )}
              {Object.entries(document.metadata)
                .slice(0, 3)
                .map(([key, value], i) => (
                  <MetadataBadge
                    key={i}
                    icon={FiTag}
                    value={`${key}=${value}`}
                  />
                ))}
            </div>
          )}

          {/* Content preview */}
          {summary && (
            <div className="mt-2 p-3 rounded-08 bg-background-neutral-01/50">
              <Text as="p" secondaryBody text03 className="line-clamp-6 whitespace-pre-wrap">
                {summary}
              </Text>
            </div>
          )}

          {/* Action button */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onOpenDocument();
            }}
            className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all cursor-pointer"
            style={{
              backgroundColor: "color-mix(in srgb, var(--virtualai-accent, var(--theme-primary-05)) 10%, var(--background-neutral-01) 90%)",
              color: "var(--virtualai-accent, var(--theme-primary-05))",
            }}
          >
            <SvgExternalLink className="w-3.5 h-3.5" />
            Open Document
          </button>
        </div>
      )}
    </div>
  );
}

export default function CitedSourcesModal({
  open,
  onClose,
  citedDocuments,
  otherDocuments,
  setPresentingDocument,
}: CitedSourcesModalProps) {
  const [expandedDocId, setExpandedDocId] = useState<string | null>(
    // Auto-expand first cited source
    citedDocuments[0]?.document_id ?? null
  );

  const handleToggle = (docId: string) => {
    setExpandedDocId((prev) => (prev === docId ? null : docId));
  };

  const handleOpenDocument = (document: OnyxDocument) => {
    openDocument(document, setPresentingDocument);
  };

  const totalCount = citedDocuments.length + otherDocuments.length;

  return (
    <Modal open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <Modal.Content width="sm" height="lg">
        <Modal.Header
          icon={SvgBookOpen}
          title={`Cited Sources (${citedDocuments.length})`}
          description={
            otherDocuments.length > 0
              ? `${totalCount} sources found, ${citedDocuments.length} cited in response`
              : undefined
          }
          onClose={onClose}
        />
        <Modal.Body>
          <div className="flex flex-col gap-2">
            {/* Cited sources */}
            {citedDocuments.map((doc, index) => (
              <SourceCard
                key={doc.document_id}
                document={doc}
                isExpanded={expandedDocId === doc.document_id}
                onToggle={() => handleToggle(doc.document_id)}
                onOpenDocument={() => handleOpenDocument(doc)}
                index={index}
              />
            ))}

            {/* Other retrieved sources */}
            {otherDocuments.length > 0 && (
              <>
                <div className="flex items-center gap-2 mt-3 mb-1">
                  <div className="h-px flex-1 bg-border-01" />
                  <Text as="span" secondaryBody text03 className="text-xs uppercase tracking-wider flex-shrink-0">
                    Other Sources
                  </Text>
                  <div className="h-px flex-1 bg-border-01" />
                </div>

                {otherDocuments.map((doc, index) => (
                  <SourceCard
                    key={doc.document_id}
                    document={doc}
                    isExpanded={expandedDocId === doc.document_id}
                    onToggle={() => handleToggle(doc.document_id)}
                    onOpenDocument={() => handleOpenDocument(doc)}
                    index={citedDocuments.length + index}
                  />
                ))}
              </>
            )}

            {citedDocuments.length === 0 && otherDocuments.length === 0 && (
              <div className="py-8 text-center">
                <Text secondaryBody text03>No sources found for this response.</Text>
              </div>
            )}
          </div>
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}
