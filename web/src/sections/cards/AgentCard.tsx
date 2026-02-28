"use client";

import React, { useMemo, useCallback } from "react";
import { MinimalPersonaSnapshot } from "@/app/admin/assistants/interfaces";
import AgentAvatar from "@/refresh-components/avatars/AgentAvatar";
import IconButton from "@/refresh-components/buttons/IconButton";
import { usePinnedAgents, useAgent } from "@/hooks/useAgents";
import { cn, noProp } from "@/lib/utils";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import { usePaidEnterpriseFeaturesEnabled } from "@/components/settings/usePaidEnterpriseFeaturesEnabled";
import { checkUserOwnsAssistant, updateAgentSharedStatus } from "@/lib/agents";
import { useUser } from "@/providers/UserProvider";
import Text from "@/refresh-components/texts/Text";
import {
  SvgBarChart,
  SvgChevronRight,
  SvgEdit,
  SvgPin,
  SvgPinned,
  SvgShare,
} from "@opal/icons";
import { useCreateModal } from "@/refresh-components/contexts/ModalContext";
import ShareAgentModal from "@/sections/modals/ShareAgentModal";
import AgentViewerModal from "@/sections/modals/AgentViewerModal";
import { toast } from "@/hooks/useToast";
import { Interactive } from "@opal/core";
import { getLabelColor } from "@/lib/labelColors";

export interface AgentCardProps {
  agent: MinimalPersonaSnapshot;
  onLabelClick?: (labelId: number) => void;
}

export default function AgentCard({ agent, onLabelClick }: AgentCardProps) {
  const router = useRouter();
  const { pinnedAgents, togglePinnedAgent } = usePinnedAgents();
  const pinned = useMemo(
    () => pinnedAgents.some((pinnedAgent) => pinnedAgent.id === agent.id),
    [agent.id, pinnedAgents]
  );
  const { user } = useUser();
  const isPaidEnterpriseFeaturesEnabled = usePaidEnterpriseFeaturesEnabled();
  const isOwnedByUser = checkUserOwnsAssistant(user, agent);
  const [hovered, setHovered] = React.useState(false);
  const shareAgentModal = useCreateModal();
  const agentViewerModal = useCreateModal();
  const { agent: fullAgent, refresh: refreshAgent } = useAgent(agent.id);

  // Handle sharing agent
  const handleShare = useCallback(
    async (userIds: string[], groupIds: number[], isPublic: boolean) => {
      const error = await updateAgentSharedStatus(
        agent.id,
        userIds,
        groupIds,
        isPublic,
        isPaidEnterpriseFeaturesEnabled
      );

      if (error) {
        toast.error(`Failed to share agent: ${error}`);
      } else {
        refreshAgent();
        shareAgentModal.toggle(false);
      }
    },
    [agent.id, isPaidEnterpriseFeaturesEnabled, refreshAgent]
  );

  return (
    <>
      <shareAgentModal.Provider>
        <ShareAgentModal
          agentId={agent.id}
          userIds={fullAgent?.users?.map((u) => u.id) ?? []}
          groupIds={fullAgent?.groups ?? []}
          isPublic={fullAgent?.is_public ?? false}
          onShare={handleShare}
        />
      </shareAgentModal.Provider>

      <agentViewerModal.Provider>
        {fullAgent && <AgentViewerModal agent={fullAgent} />}
      </agentViewerModal.Provider>

      <Interactive.Base
        onClick={() => agentViewerModal.toggle(true)}
        group="group/AgentCard"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        variant="none"
      >
        <div
          className={cn(
            "flex flex-row items-center gap-3 px-3 py-3 rounded-12",
            "transition-colors duration-150 cursor-pointer",
            "hover:bg-background-neutral-02"
          )}
        >
          {/* Avatar */}
          <div className="flex-shrink-0">
            <AgentAvatar agent={agent} size={36} />
          </div>

          {/* Name + Description + Labels */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              <Text as="p" mainContentBody className="truncate font-medium">
                {agent.name}
              </Text>
              {agent.workflow_id && (
                <span
                  className="inline-flex items-center px-1.5 py-0.5 rounded text-[0.625rem] leading-tight font-semibold bg-background-accent-01 text-text-accent whitespace-nowrap"
                  title="Multi-Agent Workflow"
                >
                  Workflow
                </span>
              )}
            </div>
            {agent.description && (
              <Text as="p" secondaryBody text03 className="truncate">
                {agent.description}
              </Text>
            )}
            {agent.labels && agent.labels.length > 0 && (
              <div className="flex items-center gap-1 flex-wrap mt-1">
                {agent.labels.slice(0, 4).map((label) => {
                  const color = getLabelColor(label.id);
                  return (
                    <button
                      key={label.id}
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onLabelClick?.(label.id);
                      }}
                      className={cn(
                        "inline-flex items-center px-2 py-0.5 rounded-full text-[0.6875rem] leading-tight font-medium",
                        "transition-opacity hover:opacity-80 cursor-pointer",
                        color.bg,
                        color.text
                      )}
                    >
                      {label.name}
                    </button>
                  );
                })}
                {agent.labels.length > 4 && (
                  <span className="text-text-03 text-[0.6875rem]">
                    +{agent.labels.length - 4}
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Hover actions — replace chevron on hover */}
          <div className="flex flex-row items-center flex-shrink-0">
            {/* Action buttons — visible on hover */}
            <div className="hidden group-hover/AgentCard:flex flex-row items-center">
              {isOwnedByUser && isPaidEnterpriseFeaturesEnabled && (
                <IconButton
                  icon={SvgBarChart}
                  tertiary
                  onClick={noProp(() =>
                    router.push(
                      `/ee/assistants/stats/${agent.id}` as Route
                    )
                  )}
                  tooltip="View Agent Stats"
                />
              )}
              {isOwnedByUser && (
                <IconButton
                  icon={SvgEdit}
                  tertiary
                  onClick={noProp(() =>
                    router.push(
                      agent.workflow_id
                        ? (`/admin/workflows/edit/${agent.workflow_id}` as Route)
                        : (`/app/agents/edit/${agent.id}` as Route)
                    )
                  )}
                  tooltip={agent.workflow_id ? "Edit Workflow" : "Edit Agent"}
                />
              )}
              {isOwnedByUser && (
                <IconButton
                  icon={SvgShare}
                  tertiary
                  onClick={noProp(() => shareAgentModal.toggle(true))}
                  tooltip="Share Agent"
                />
              )}
              <IconButton
                icon={pinned ? SvgPinned : SvgPin}
                tertiary
                onClick={noProp(() => togglePinnedAgent(agent, !pinned))}
                tooltip={pinned ? "Unpin from Sidebar" : "Pin to Sidebar"}
                transient={hovered && pinned}
              />
            </div>

            {/* Chevron — hidden on hover */}
            <SvgChevronRight
              className={cn(
                "w-5 h-5 text-text-02 transition-opacity",
                "group-hover/AgentCard:hidden"
              )}
            />
          </div>
        </div>
      </Interactive.Base>
    </>
  );
}
