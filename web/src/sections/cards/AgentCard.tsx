"use client";

import React, { useMemo, useCallback } from "react";
import { MinimalPersonaSnapshot } from "@/app/admin/assistants/interfaces";
import AgentAvatar from "@/refresh-components/avatars/AgentAvatar";
import Button from "@/refresh-components/buttons/Button";
import { useAppRouter } from "@/hooks/appNavigation";
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
  SvgActions,
  SvgBarChart,
  SvgBubbleText,
  SvgEdit,
  SvgPin,
  SvgPinned,
  SvgShare,
  SvgUser,
} from "@opal/icons";
import { useCreateModal } from "@/refresh-components/contexts/ModalContext";
import ShareAgentModal from "@/sections/modals/ShareAgentModal";
import AgentViewerModal from "@/sections/modals/AgentViewerModal";
import { toast } from "@/hooks/useToast";
import { Interactive } from "@opal/core";
import { Card } from "@/refresh-components/cards";

export interface AgentCardProps {
  agent: MinimalPersonaSnapshot;
}

export default function AgentCard({ agent }: AgentCardProps) {
  const route = useAppRouter();
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

  // Start chat and auto-pin unpinned agents to the sidebar
  const handleStartChat = useCallback(() => {
    if (!pinned) {
      togglePinnedAgent(agent, true);
    }
    route({ agentId: agent.id });
  }, [pinned, togglePinnedAgent, agent, route]);

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
        // Revalidate the agent data to reflect the changes
        refreshAgent();
        shareAgentModal.toggle(false);
      }
    },
    [agent.id, isPaidEnterpriseFeaturesEnabled, refreshAgent]
  );

  const toolCount = agent.tools.length;
  const creatorLabel = agent.owner?.email || "VertualAI";

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
        <Card padding={0} gap={0} height="full">
          <div className="flex flex-col p-3 gap-2.5 w-full">
            {/* Top row: Avatar + Name + Action buttons */}
            <div className="flex flex-row items-start gap-2.5">
              <div className="flex-shrink-0 mt-0.5">
                <AgentAvatar agent={agent} size={32} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex flex-row items-center justify-between gap-1">
                  <Text as="p" mainContentBody className="truncate font-medium">
                    {agent.name}
                  </Text>
                  {/* Hover action buttons */}
                  <div className="flex flex-row items-center flex-shrink-0">
                    {isOwnedByUser && isPaidEnterpriseFeaturesEnabled && (
                      <IconButton
                        icon={SvgBarChart}
                        tertiary
                        onClick={noProp(() =>
                          router.push(`/ee/assistants/stats/${agent.id}` as Route)
                        )}
                        tooltip="View Agent Stats"
                        className="hidden group-hover/AgentCard:flex"
                      />
                    )}
                    {isOwnedByUser && (
                      <IconButton
                        icon={SvgEdit}
                        tertiary
                        onClick={noProp(() =>
                          router.push(`/app/agents/edit/${agent.id}` as Route)
                        )}
                        tooltip="Edit Agent"
                        className="hidden group-hover/AgentCard:flex"
                      />
                    )}
                    {isOwnedByUser && (
                      <IconButton
                        icon={SvgShare}
                        tertiary
                        onClick={noProp(() => shareAgentModal.toggle(true))}
                        tooltip="Share Agent"
                        className="hidden group-hover/AgentCard:flex"
                      />
                    )}
                    <IconButton
                      icon={pinned ? SvgPinned : SvgPin}
                      tertiary
                      onClick={noProp(() => togglePinnedAgent(agent, !pinned))}
                      tooltip={pinned ? "Unpin from Sidebar" : "Pin to Sidebar"}
                      transient={hovered && pinned}
                      className={cn(
                        !pinned && "hidden group-hover/AgentCard:flex"
                      )}
                    />
                  </div>
                </div>
                {/* Description — 2 lines max */}
                {agent.description && (
                  <Text
                    as="p"
                    secondaryBody
                    text03
                    className="line-clamp-2 mt-0.5"
                  >
                    {agent.description}
                  </Text>
                )}
              </div>
            </div>

            {/* Bottom row: metadata + Start Chat */}
            <div className="flex flex-row items-center justify-between gap-2">
              <div className="flex flex-row items-center gap-3 min-w-0">
                <div className="flex flex-row items-center gap-1 min-w-0">
                  <SvgUser className="w-3 h-3 flex-shrink-0 text-text-02" />
                  <Text as="span" secondaryBody text02 className="truncate">
                    {creatorLabel}
                  </Text>
                </div>
                {toolCount > 0 && (
                  <div className="flex flex-row items-center gap-1 flex-shrink-0">
                    <SvgActions className="w-3 h-3 text-text-02" />
                    <Text as="span" secondaryBody text02>
                      {toolCount}
                    </Text>
                  </div>
                )}
              </div>
              <div className="flex-shrink-0 opacity-0 group-hover/AgentCard:opacity-100 transition-opacity">
                <Button
                  tertiary
                  rightIcon={SvgBubbleText}
                  onClick={noProp(handleStartChat)}
                >
                  Start Chat
                </Button>
              </div>
            </div>
          </div>
        </Card>
      </Interactive.Base>
    </>
  );
}
