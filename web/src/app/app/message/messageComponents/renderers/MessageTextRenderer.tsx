import React, { useEffect, useMemo, useState } from "react";
import Text from "@/refresh-components/texts/Text";
import { FiDownload } from "react-icons/fi";

import {
  ChatPacket,
  MessageDelta,
  PacketType,
  StopReason,
} from "../../../services/streamingModels";
import { MessageRenderer, FullChatState } from "../interfaces";
import { isFinalAnswerComplete } from "../../../services/packetUtils";
import { useMarkdownRenderer } from "../markdownUtils";
import { BlinkingDot } from "../../BlinkingDot";
import { buildImgUrl } from "../../../components/files/images/utils";

// Control the rate of packet streaming (packets per second)
const PACKET_DELAY_MS = 10;

export const MessageTextRenderer: MessageRenderer<
  ChatPacket,
  FullChatState
> = ({
  packets,
  state,
  onComplete,
  renderType,
  animate,
  stopPacketSeen,
  stopReason,
  children,
}) => {
  // If we're animating and the final answer is already complete, show more packets initially
  const initialPacketCount = animate
    ? packets.length > 0
      ? 1 // Otherwise start with 1 packet
      : 0
    : -1; // Show all if not animating

  const [displayedPacketCount, setDisplayedPacketCount] =
    useState(initialPacketCount);

  // Get the full content from all packets
  const fullContent = packets
    .map((packet) => {
      if (
        packet.obj.type === PacketType.MESSAGE_DELTA ||
        packet.obj.type === PacketType.MESSAGE_START
      ) {
        return packet.obj.content;
      }
      return "";
    })
    .join("");

  // Animation effect - gradually increase displayed packets at controlled rate
  useEffect(() => {
    if (!animate) {
      setDisplayedPacketCount(-1); // Show all packets
      return;
    }

    if (displayedPacketCount >= 0 && displayedPacketCount < packets.length) {
      const timer = setTimeout(() => {
        setDisplayedPacketCount((prev) => Math.min(prev + 1, packets.length));
      }, PACKET_DELAY_MS);

      return () => clearTimeout(timer);
    }
  }, [animate, displayedPacketCount, packets.length]);

  // Reset displayed count when packet array changes significantly (e.g., new message)
  useEffect(() => {
    if (animate && packets.length < displayedPacketCount) {
      const resetCount = isFinalAnswerComplete(packets)
        ? Math.min(10, packets.length)
        : packets.length > 0
          ? 1
          : 0;
      setDisplayedPacketCount(resetCount);
    }
  }, [animate, packets.length, displayedPacketCount]);

  // Only mark as complete when all packets are received AND displayed
  useEffect(() => {
    if (isFinalAnswerComplete(packets)) {
      // If animating, wait until all packets are displayed
      if (
        animate &&
        displayedPacketCount >= 0 &&
        displayedPacketCount < packets.length
      ) {
        return;
      }
      onComplete();
    }
  }, [packets, onComplete, animate, displayedPacketCount]);

  // Get content based on displayed packet count
  const content = useMemo(() => {
    if (!animate || displayedPacketCount === -1) {
      return fullContent; // Show all content
    }

    // Only show content from packets up to displayedPacketCount
    return packets
      .slice(0, displayedPacketCount)
      .map((packet) => {
        if (
          packet.obj.type === PacketType.MESSAGE_DELTA ||
          packet.obj.type === PacketType.MESSAGE_START
        ) {
          return packet.obj.content;
        }
        return "";
      })
      .join("");
  }, [animate, displayedPacketCount, fullContent, packets]);

  // Extract file_ids and file_names from message_delta packets
  const fileDownloads = useMemo(() => {
    const ids: string[] = [];
    const names: string[] = [];
    for (const packet of packets) {
      if (packet.obj.type === PacketType.MESSAGE_DELTA) {
        const delta = packet.obj as MessageDelta;
        if (delta.file_ids) {
          delta.file_ids.forEach((fid, idx) => {
            ids.push(fid);
            names.push(
              delta.file_names?.[idx] || `File ${ids.length}`
            );
          });
        }
      }
    }
    return ids.length > 0 ? { ids, names } : null;
  }, [packets]);

  const { renderedContent } = useMarkdownRenderer(
    // the [*]() is a hack to show a blinking dot when the packet is not complete
    stopPacketSeen ? content : content + " [*]() ",
    state,
    "font-main-content-body"
  );

  const wasUserCancelled = stopReason === StopReason.USER_CANCELLED;

  return children([
    {
      icon: null,
      status: null,
      content:
        content.length > 0 || packets.length > 0 ? (
          <>
            {renderedContent}
            {fileDownloads && (
              <div className="mt-4 flex flex-col gap-2">
                {fileDownloads.ids.map((fid, idx) => (
                  <a
                    key={fid}
                    href={buildImgUrl(fid)}
                    download={fileDownloads.names[idx]}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-border bg-background-subtle hover:bg-background-stronger transition-colors text-sm font-medium w-fit"
                  >
                    <FiDownload className="w-4 h-4" />
                    {fileDownloads.names[idx]}
                  </a>
                ))}
              </div>
            )}
            {wasUserCancelled && (
              <Text as="p" secondaryBody text04>
                User has stopped generation
              </Text>
            )}
          </>
        ) : (
          <BlinkingDot addMargin />
        ),
    },
  ]);
};
