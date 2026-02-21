"use client";

import React from "react";
import { SvgFold, SvgExpand } from "@opal/icons";
import { Button } from "@opal/components";
import { useStreamingDuration } from "../hooks/useStreamingDuration";
import { formatDurationSeconds } from "@/lib/time";
import {
  SpinnerRing,
  WaveDots,
} from "@/app/app/message/ThinkingIndicator";

export interface StreamingHeaderProps {
  headerText: string;
  collapsible: boolean;
  buttonTitle?: string;
  isExpanded: boolean;
  onToggle: () => void;
  streamingStartTime?: number;
  /** Tool processing duration from backend (freezes timer when available) */
  toolProcessingDuration?: number;
}

/** Header during streaming — spinner ring + status text + wave dots */
export const StreamingHeader = React.memo(function StreamingHeader({
  headerText,
  collapsible,
  buttonTitle,
  isExpanded,
  onToggle,
  streamingStartTime,
  toolProcessingDuration,
}: StreamingHeaderProps) {
  // Use backend duration when available, otherwise continue live timer
  const elapsedSeconds = useStreamingDuration(
    toolProcessingDuration === undefined, // Stop updating when we have backend duration
    streamingStartTime,
    toolProcessingDuration
  );
  const showElapsedTime = streamingStartTime && elapsedSeconds > 0;

  return (
    <>
      <div className="px-[var(--timeline-header-text-padding-x)] py-[var(--timeline-header-text-padding-y)] flex items-center gap-2">
        <SpinnerRing size={14} />
        <span className="font-main-ui-action text-text-04">
          {headerText}
        </span>
        {showElapsedTime && (
          <span className="font-secondary-body text-text-02">
            {formatDurationSeconds(elapsedSeconds)}
          </span>
        )}
        <WaveDots />
      </div>

      {collapsible &&
        (buttonTitle ? (
          <Button
            prominence="tertiary"
            size="md"
            onClick={onToggle}
            rightIcon={isExpanded ? SvgFold : SvgExpand}
            aria-expanded={isExpanded}
          >
            {buttonTitle}
          </Button>
        ) : (
          <Button
            prominence="tertiary"
            size="md"
            onClick={onToggle}
            icon={isExpanded ? SvgFold : SvgExpand}
            aria-label={isExpanded ? "Collapse timeline" : "Expand timeline"}
            aria-expanded={isExpanded}
          />
        ))}
    </>
  );
});
