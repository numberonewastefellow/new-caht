"use client";

import React, { useMemo } from "react";
import Link from "next/link";
import { ChatSessionMorePopup } from "@/components/sidebar/ChatSessionMorePopup";
import { useWorkspacesContext } from "@/providers/WorkspacesContext";
import { ChatSession } from "@/app/app/interfaces";
import AgentAvatar from "@/refresh-components/avatars/AgentAvatar";
import { useAgents } from "@/hooks/useAgents";
import useAppFocus from "@/hooks/useAppFocus";
import { formatRelativeTime } from "./workspace_utils";
import { swatchIndexForKey } from "./workspace-v2/workspaceTheme";
import Text from "@/refresh-components/texts/Text";
import { cn } from "@/lib/utils";
import { UNNAMED_CHAT } from "@/lib/constants";
import ChatSessionSkeleton from "@/refresh-components/skeletons/ChatSessionSkeleton";
import { SvgBubbleText, SvgClock } from "@opal/icons";

export default function WorkspaceChatSessionList({
  searchQuery,
}: {
  searchQuery?: string;
} = {}) {
  const {
    currentWorkspaceDetails,
    currentWorkspaceId,
    refreshCurrentWorkspaceDetails,
    isLoadingWorkspaceDetails,
  } = useWorkspacesContext();
  const { agents: assistants } = useAgents();
  const appFocus = useAppFocus();
  const activeChatId = appFocus.isChat() ? appFocus.getId() : null;
  const [isRenamingChat, setIsRenamingChat] = React.useState<string | null>(
    null
  );
  const [hoveredChatId, setHoveredChatId] = React.useState<string | null>(null);

  const workspaceChats: ChatSession[] = useMemo(() => {
    const sessions = currentWorkspaceDetails?.workspace?.chat_sessions || [];
    const sorted = [...sessions].sort(
      (a, b) =>
        new Date(b.time_updated).getTime() - new Date(a.time_updated).getTime()
    );
    const q = searchQuery?.trim().toLowerCase();
    return q
      ? sorted.filter((c) => (c.name || "").toLowerCase().includes(q))
      : sorted;
  }, [currentWorkspaceDetails?.workspace?.chat_sessions, searchQuery]);

  if (!currentWorkspaceId) return null;

  return (
    <div className="flex flex-col gap-2 px-2 w-full mx-auto mt-4">
      <div className="flex items-center pl-2">
        <span className="text-[13px] font-medium text-text-03">
          Chats
        </span>
      </div>

      {isLoadingWorkspaceDetails && !currentWorkspaceDetails ? (
        <div className="flex flex-col gap-2">
          <ChatSessionSkeleton />
          <ChatSessionSkeleton />
          <ChatSessionSkeleton />
        </div>
      ) : workspaceChats.length === 0 ? (
        <Text as="p" text02 secondaryBody className="p-2">
          No chats yet.
        </Text>
      ) : (
        <div className="flex flex-col gap-0.5">
          {workspaceChats.map((chat) => {
            const isActive = chat.id === activeChatId;
            const agentIdToDefault =
              currentWorkspaceDetails?.agent_id_to_is_default || {};
            const isCustomAgent =
              agentIdToDefault[chat.agent_id] === false;
            const assistant = isCustomAgent
              ? assistants.find((a) => a.id === chat.agent_id)
              : undefined;
            const n = swatchIndexForKey(chat.id);
            return (
              <Link
                key={chat.id}
                href={{
                  pathname: "/app",
                  query: { chatId: chat.id, workspaceId: currentWorkspaceId },
                }}
                className="relative block w-full"
                onMouseEnter={() => setHoveredChatId(chat.id)}
                onMouseLeave={() => setHoveredChatId(null)}
              >
                <div
                  className={cn(
                    "flex items-center gap-2.5 rounded-10 px-2 py-1.5 transition-colors",
                    !isActive &&
                      hoveredChatId === chat.id &&
                      "bg-background-tint-02"
                  )}
                  style={
                    isActive
                      ? { backgroundColor: "var(--virtualai-accent-subtle)" }
                      : undefined
                  }
                >
                  {/* Per-chat colored icon tile (custom-agent chats keep the avatar) */}
                  {assistant ? (
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center">
                      <AgentAvatar agent={assistant} size={20} />
                    </div>
                  ) : (
                    <span
                      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg"
                      style={{
                        backgroundColor: `color-mix(in srgb, var(--ws-swatch-${n}-from) 16%, transparent)`,
                      }}
                    >
                      <SvgBubbleText
                        className="h-3.5 w-3.5 stroke-current"
                        style={{ color: `var(--ws-swatch-${n}-from)` }}
                      />
                    </span>
                  )}

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-1">
                      <Text
                        as="p"
                        text04
                        mainUiBody
                        nowrap
                        className="truncate"
                        title={chat.name}
                      >
                        {chat.name || UNNAMED_CHAT}
                      </Text>
                      <ChatSessionMorePopup
                        chatSession={chat}
                        workspaceId={currentWorkspaceId}
                        isRenamingChat={isRenamingChat === chat.id}
                        setIsRenamingChat={(value) =>
                          setIsRenamingChat(value ? chat.id : null)
                        }
                        search={false}
                        afterDelete={() => {
                          refreshCurrentWorkspaceDetails();
                        }}
                        afterMove={() => {
                          refreshCurrentWorkspaceDetails();
                        }}
                        afterRemoveFromWorkspace={() => {
                          refreshCurrentWorkspaceDetails();
                        }}
                        iconSize={20}
                        isVisible={hoveredChatId === chat.id}
                      />
                    </div>
                    <div className="flex items-center gap-1 text-[11px] text-text-03">
                      <SvgClock className="h-3 w-3 stroke-text-02" />
                      {formatRelativeTime(chat.time_updated)}
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
