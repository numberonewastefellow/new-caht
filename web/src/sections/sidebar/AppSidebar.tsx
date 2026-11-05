"use client";

import { useCallback, memo, useMemo, useState, useEffect, useRef } from "react";
import useSWR from "swr";
import { useRouter } from "next/navigation";
import { useSettingsContext } from "@/providers/SettingsProvider";
import { MinimalAgentSnapshot } from "@/app/admin/assistants/interfaces";
import Text from "@/refresh-components/texts/Text";
import ChatButton from "@/sections/sidebar/ChatButton";
import AgentButton from "@/sections/sidebar/AgentButton";
import { DragEndEvent } from "@dnd-kit/core";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  pointerWithin,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useDroppable } from "@dnd-kit/core";
import {
  restrictToFirstScrollableAncestor,
  restrictToVerticalAxis,
} from "@dnd-kit/modifiers";
import SidebarSection from "@/sections/sidebar/SidebarSection";
import useChatSessions from "@/hooks/useChatSessions";
import { useWorkspaces } from "@/lib/hooks/useWorkspaces";
import { useAgents, useCurrentAgent, usePinnedAgents } from "@/hooks/useAgents";
import { useAppSidebarContext } from "@/providers/AppSidebarProvider";
import CreateWorkspaceModal from "@/components/modals/CreateWorkspaceModal";
import MoveCustomAgentChatModal from "@/components/modals/MoveCustomAgentChatModal";
import { useWorkspacesContext } from "@/providers/WorkspacesContext";
import { removeChatSessionFromWorkspace } from "@/app/app/workspaces/workspacesService";
import type { Workspace } from "@/app/app/workspaces/workspacesService";
import SidebarWrapper from "@/sections/sidebar/SidebarWrapper";
import { cn } from "@/lib/utils";
import {
  DRAG_TYPES,
  DEFAULT_AGENT_ID,
  FEATURE_FLAGS,
  LOCAL_STORAGE_KEYS,
} from "@/sections/sidebar/constants";
import { showErrorNotification, handleMoveOperation } from "./sidebarUtils";
import SidebarTab from "@/refresh-components/buttons/SidebarTab";
import { ChatSession } from "@/app/app/interfaces";
import SidebarBody from "@/sections/sidebar/SidebarBody";
import { useUser } from "@/providers/UserProvider";
import useAppFocus from "@/hooks/useAppFocus";
import { useCreateModal } from "@/refresh-components/contexts/ModalContext";
import { useModalContext } from "@/components/context/ModalContext";
import useScreenSize from "@/hooks/useScreenSize";
import { SvgMoreHorizontal, SvgOmOctagon } from "@opal/icons";
import { makeColorfulIcon } from "@/refresh-components/popovers/ActionsPopover/colorfulIcons";
import ScheduledSection from "@/sections/sidebar/ScheduledSection";

// The action-row icons live in appNavItems.ts with their rows; these two are
// for the Agents section, which is not part of the nav catalog.
const ColorfulExploreAgents = makeColorfulIcon(SvgOmOctagon, "sidebar_agents");
const ColorfulMoreAgents = makeColorfulIcon(SvgMoreHorizontal, "sidebar_agents");

/** Maps a catalog focus key to the matching `useAppFocus()` check. */
const APP_NAV_ACTIVE_CHECKS: Record<
  AppNavFocusKey,
  (focus: ReturnType<typeof useAppFocus>) => boolean
> = {
  newSession: (focus) => focus.isNewSession(),
  workspacesDashboard: (focus) => focus.isWorkspacesDashboard(),
  workflowsGallery: (focus) => focus.isWorkflowsGallery(),
  schedules: (focus) => focus.isSchedules(),
};
import BuildModeIntroBackground from "@/app/craft/components/IntroBackground";
import BuildModeIntroContent from "@/app/craft/components/IntroContent";
import { CRAFT_PATH } from "@/app/craft/v1/constants";
import { usePostHog } from "posthog-js/react";
import { motion, AnimatePresence } from "motion/react";
import {
  Notification,
  NotificationType,
} from "@/app/admin/settings/interfaces";
import { errorHandlingFetcher } from "@/lib/fetcher";
import UserAvatarPopover from "@/sections/sidebar/UserAvatarPopover";
import AdminEntryTab from "@/sections/sidebar/AdminEntryTab";
import useNavVersion from "@/hooks/useNavVersion";
import {
  getAppNavItems,
  APP_NAV_GROUP_ORDER,
  type AppNavItem,
  type AppNavFocusKey,
} from "@/sections/sidebar/appNavItems";
import ChatSearchCommandMenu from "@/sections/sidebar/ChatSearchCommandMenu";
import { useAppMode } from "@/providers/AppModeProvider";
import { useQueryController } from "@/providers/QueryControllerProvider";

// Visible-agents = pinned-agents + current-agent (if current-agent not in pinned-agents)
// OR Visible-agents = pinned-agents (if current-agent in pinned-agents)
function buildVisibleAgents(
  pinnedAgents: MinimalAgentSnapshot[],
  currentAgent: MinimalAgentSnapshot | null
): [MinimalAgentSnapshot[], boolean] {
  /* NOTE: The unified agent (id = 0) is not visible in the sidebar,
  so we filter it out. */
  if (!currentAgent)
    return [pinnedAgents.filter((agent) => agent.id !== 0), false];
  const currentAgentIsPinned = pinnedAgents.some(
    (pinnedAgent) => pinnedAgent.id === currentAgent.id
  );
  const visibleAgents = (
    currentAgentIsPinned ? pinnedAgents : [...pinnedAgents, currentAgent]
  ).filter((agent) => agent.id !== 0);

  return [visibleAgents, currentAgentIsPinned];
}

const INITIAL_VISIBLE_CHATS = 15;
const LOAD_MORE_INCREMENT = 15;

interface RecentsSectionProps {
  chatSessions: ChatSession[];
}

function RecentsSection({ chatSessions }: RecentsSectionProps) {
  const [visibleCount, setVisibleCount] = useState(INITIAL_VISIBLE_CHATS);
  const { setNodeRef, isOver } = useDroppable({
    id: DRAG_TYPES.RECENTS,
    data: {
      type: DRAG_TYPES.RECENTS,
    },
  });

  const visibleSessions = chatSessions.slice(0, visibleCount);
  const hasMore = chatSessions.length > visibleCount;
  const remainingCount = chatSessions.length - visibleCount;

  return (
    <div
      ref={setNodeRef}
      className={cn(
        "transition-colors duration-200 rounded-08 h-full",
        isOver && "bg-background-tint-03"
      )}
    >
      <SidebarSection title="Your chats">
        {chatSessions.length === 0 ? (
          <Text as="p" text01 className="px-3">
            Try sending a message! Your chat history will appear here.
          </Text>
        ) : (
          <>
            {visibleSessions.map((chatSession) => (
              <ChatButton
                key={chatSession.id}
                chatSession={chatSession}
                draggable
              />
            ))}
            {hasMore && (
              <button
                type="button"
                onClick={() =>
                  setVisibleCount((prev) => prev + LOAD_MORE_INCREMENT)
                }
                className={cn(
                  "w-full px-3 py-1.5 text-xs font-medium text-text-03",
                  "hover:text-text-05 hover:bg-background-tint-02",
                  "rounded-08 transition-colors duration-150 text-left"
                )}
              >
                View more ({remainingCount})
              </button>
            )}
          </>
        )}
      </SidebarSection>
    </div>
  );
}

interface AppSidebarInnerProps {
  folded: boolean;
  onFoldClick: () => void;
}

const MemoizedAppSidebarInner = memo(
  ({ folded, onFoldClick }: AppSidebarInnerProps) => {
    const router = useRouter();
    const combinedSettings = useSettingsContext();
    const posthog = usePostHog();
    const { newTenantInfo, invitationInfo } = useModalContext();
    const { setAppMode } = useAppMode();
    const { reset } = useQueryController();

    // Use SWR hooks for data fetching
    const {
      chatSessions,
      refreshChatSessions,
      isLoading: isLoadingChatSessions,
    } = useChatSessions();
    const { refreshWorkspaces, isLoading: isLoadingWorkspaces } = useWorkspaces();
    const { isLoading: isLoadingAgents } = useAgents();
    const currentAgent = useCurrentAgent();
    const {
      pinnedAgents,
      updatePinnedAgents,
      isLoading: isLoadingPinnedAgents,
    } = usePinnedAgents();

    // Wait for ALL dynamic data before showing any sections
    const isLoadingDynamicContent =
      isLoadingChatSessions ||
      isLoadingWorkspaces ||
      isLoadingAgents ||
      isLoadingPinnedAgents;

    // Still need some context for stateful operations
    const { refreshCurrentWorkspaceDetails, currentWorkspaceId } =
      useWorkspacesContext();

    // State for custom agent modal
    const [pendingMoveChatSession, setPendingMoveChatSession] =
      useState<ChatSession | null>(null);
    const [pendingMoveWorkspaceId, setPendingMoveWorkspaceId] = useState<
      number | null
    >(null);
    const [showMoveCustomAgentModal, setShowMoveCustomAgentModal] =
      useState(false);

    // Fetch notifications for build mode intro
    const { data: notifications, mutate: mutateNotifications } = useSWR<
      Notification[]
    >("/api/signals", errorHandlingFetcher);

    // Check if VertualAI Craft is enabled via settings (backed by PostHog feature flag)
    // Only explicit true enables the feature; false or undefined = disabled
    const isOmCraftEnabled =
      combinedSettings?.settings?.om_craft_enabled === true;

    // Find build_mode feature announcement notification (only if VertualAI Craft is enabled)
    const buildModeNotification = isOmCraftEnabled
      ? notifications?.find(
          (n) =>
            n.notif_type === NotificationType.FEATURE_ANNOUNCEMENT &&
            n.additional_data?.feature === "build_mode" &&
            !n.dismissed
        )
      : undefined;

    // State for intro animation overlay
    const [showIntroAnimation, setShowIntroAnimation] = useState(false);
    // Track if auto-trigger has fired (prevents race condition during dismiss)
    const hasAutoTriggeredRef = useRef(false);

    // Auto-show intro once when there's an undismissed notification
    // Don't show if tenant/invitation modal is open (e.g., "join existing team" modal)
    // Gated by PostHog feature flag: if `craft-animation-disabled` is true (or
    // PostHog is unavailable), skip the auto-show entirely.
    const isCraftAnimationDisabled =
      posthog?.isFeatureEnabled(FEATURE_FLAGS.CRAFT_ANIMATION_DISABLED) ?? true;
    const hasTenantModal = !!(newTenantInfo || invitationInfo);
    useEffect(() => {
      if (
        isOmCraftEnabled &&
        buildModeNotification &&
        !hasAutoTriggeredRef.current &&
        !hasTenantModal &&
        !isCraftAnimationDisabled
      ) {
        hasAutoTriggeredRef.current = true;
        setShowIntroAnimation(true);
      }
    }, [
      buildModeNotification,
      isOmCraftEnabled,
      hasTenantModal,
      isCraftAnimationDisabled,
    ]);

    // Dismiss the build mode notification
    const dismissBuildModeNotification = useCallback(async () => {
      if (!buildModeNotification) return;
      try {
        await fetch(`/api/signals/${buildModeNotification.id}/dismiss`, {
          method: "POST",
        });
        mutateNotifications();
      } catch (error) {
        console.error("Error dismissing notification:", error);
      }
    }, [buildModeNotification, mutateNotifications]);

    const [visibleAgents, currentAgentIsPinned] = useMemo(
      () => buildVisibleAgents(pinnedAgents, currentAgent),
      [pinnedAgents, currentAgent]
    );
    const visibleAgentIds = useMemo(
      () => visibleAgents.map((agent) => agent.id),
      [visibleAgents]
    );

    const sensors = useSensors(
      useSensor(PointerSensor, {
        activationConstraint: {
          distance: 8,
        },
      }),
      useSensor(KeyboardSensor, {
        coordinateGetter: sortableKeyboardCoordinates,
      })
    );

    // Handle agent drag and drop
    const handleAgentDragEnd = useCallback(
      (event: DragEndEvent) => {
        const { active, over } = event;
        if (!over) return;
        if (active.id === over.id) return;

        const activeIndex = visibleAgentIds.findIndex(
          (agentId) => agentId === active.id
        );
        const overIndex = visibleAgentIds.findIndex(
          (agentId) => agentId === over.id
        );

        let newPinnedAgents: MinimalAgentSnapshot[];

        if (currentAgent && !currentAgentIsPinned) {
          // This is the case in which the user is dragging the UNPINNED agent and moving it to somewhere else in the list.
          // This is an indication that we WANT to pin this agent!
          if (activeIndex === visibleAgentIds.length - 1) {
            const pinnedWithCurrent = [...pinnedAgents, currentAgent];
            newPinnedAgents = arrayMove(
              pinnedWithCurrent,
              activeIndex,
              overIndex
            );
          } else {
            // Use visibleAgents to ensure the indices match with `visibleAgentIds`
            newPinnedAgents = arrayMove(visibleAgents, activeIndex, overIndex);
          }
        } else {
          // Use visibleAgents to ensure the indices match with `visibleAgentIds`
          newPinnedAgents = arrayMove(visibleAgents, activeIndex, overIndex);
        }

        updatePinnedAgents(newPinnedAgents);
      },
      [
        visibleAgentIds,
        visibleAgents,
        pinnedAgents,
        updatePinnedAgents,
        currentAgent,
        currentAgentIsPinned,
      ]
    );

    // Perform the actual move
    async function performChatMove(
      targetWorkspaceId: number,
      chatSession: ChatSession
    ) {
      try {
        await handleMoveOperation({
          chatSession,
          targetWorkspaceId,
          refreshChatSessions,
          refreshCurrentWorkspaceDetails,
          fetchWorkspaces: refreshWorkspaces,
          currentWorkspaceId,
        });
        const workspaceRefreshPromise = currentWorkspaceId
          ? refreshCurrentWorkspaceDetails()
          : refreshWorkspaces();
        await Promise.all([refreshChatSessions(), workspaceRefreshPromise]);
      } catch (error) {
        console.error("Failed to move chat:", error);
        throw error;
      }
    }

    // Handle chat to workspace drag and drop
    const handleChatWorkspaceDragEnd = useCallback(
      async (event: DragEndEvent) => {
        const { active, over } = event;
        if (!over) return;

        const activeData = active.data.current;
        const overData = over.data.current;

        if (!activeData || !overData) {
          return;
        }

        // Check if we're dragging a chat onto a workspace
        if (
          activeData?.type === DRAG_TYPES.CHAT &&
          overData?.type === DRAG_TYPES.PROJECT
        ) {
          const chatSession = activeData.chatSession as ChatSession;
          const targetWorkspace = overData.workspace as Workspace;
          const sourceWorkspaceId = activeData.workspaceId;

          // Don't do anything if dropping on the same workspace
          if (sourceWorkspaceId === targetWorkspace.id) {
            return;
          }

          const hideModal =
            typeof window !== "undefined" &&
            window.localStorage.getItem(
              LOCAL_STORAGE_KEYS.HIDE_MOVE_CUSTOM_AGENT_MODAL
            ) === "true";

          const isChatUsingDefaultAssistant =
            chatSession.agent_id === DEFAULT_AGENT_ID;

          if (!isChatUsingDefaultAssistant && !hideModal) {
            setPendingMoveChatSession(chatSession);
            setPendingMoveWorkspaceId(targetWorkspace.id);
            setShowMoveCustomAgentModal(true);
            return;
          }

          try {
            await performChatMove(targetWorkspace.id, chatSession);
          } catch (error) {
            showErrorNotification("Failed to move chat. Please try again.");
          }
        }

        // Check if we're dragging a chat from a workspace to the Recents section
        if (
          activeData?.type === DRAG_TYPES.CHAT &&
          overData?.type === DRAG_TYPES.RECENTS
        ) {
          const chatSession = activeData.chatSession as ChatSession;
          const sourceWorkspaceId = activeData.workspaceId;

          // Only remove from workspace if it was in a workspace
          if (sourceWorkspaceId) {
            try {
              await removeChatSessionFromWorkspace(chatSession.id);
              const workspaceRefreshPromise = currentWorkspaceId
                ? refreshCurrentWorkspaceDetails()
                : refreshWorkspaces();
              await Promise.all([refreshChatSessions(), workspaceRefreshPromise]);
            } catch (error) {
              console.error("Failed to remove chat from workspace:", error);
            }
          }
        }
      },
      [
        currentWorkspaceId,
        refreshChatSessions,
        refreshCurrentWorkspaceDetails,
        refreshWorkspaces,
      ]
    );

    const { user } = useUser();
    const activeSidebarTab = useAppFocus();
    const createWorkspaceModal = useCreateModal();
    const defaultAppMode =
      (user?.preferences?.default_app_mode?.toLowerCase() as
        | "chat"
        | "search") ?? "chat";
    const navVersion = useNavVersion();

    const navItems = useMemo(
      () =>
        getAppNavItems({
          settings: combinedSettings,
          currentAgentId: currentAgent?.id,
        }),
      [combinedSettings, currentAgent]
    );

    // One catalog, two layouts. Behaviours needing app state (the chat-search
    // command menu, the create-workspace modal, query reset) are resolved here
    // so `appNavItems.ts` can stay pure data.
    const renderNavItem = useCallback(
      (item: AppNavItem) => {
        let transient = item.focusKey
          ? APP_NAV_ACTIVE_CHECKS[item.focusKey](activeSidebarTab)
          : false;
        let onClick: (() => void) | undefined;

        switch (item.behavior) {
          case "new-session":
            onClick = () => {
              // Already here: reset the composer instead of re-navigating.
              if (!activeSidebarTab.isNewSession()) return;
              setAppMode(defaultAppMode);
              reset();
            };
            break;
          case "new-workspace":
            onClick = () => createWorkspaceModal.toggle(true);
            transient = createWorkspaceModal.isOpen;
            break;
          default:
            if (item.id === "craft") {
              onClick = () => posthog?.capture("clicked_craft_in_sidebar");
            }
        }

        const tab = (
          <SidebarTab
            leftIcon={item.icon}
            folded={folded}
            href={item.href}
            transient={transient}
            lowlight={item.lowlight && !folded}
            onClick={onClick}
          >
            {item.label}
          </SidebarTab>
        );

        return (
          <div key={item.id} data-testid={item.testId}>
            {item.behavior === "search-chats" ? (
              <ChatSearchCommandMenu trigger={tab} />
            ) : (
              tab
            )}
          </div>
        );
      },
      [
        folded,
        activeSidebarTab,
        createWorkspaceModal.toggle,
        createWorkspaceModal.isOpen,
        setAppMode,
        defaultAppMode,
        reset,
        posthog,
      ]
    );

    const actionButtons = useMemo(() => {
      // v1: one flat list, as the classic sidebar had it.
      if (navVersion === "v1") {
        return (
          <div className="flex flex-col gap-0.5">
            {navItems.map(renderNavItem)}
          </div>
        );
      }

      // v2: the same rows, grouped and separated by a hairline.
      const groups = APP_NAV_GROUP_ORDER.map((id) => ({
        id,
        items: navItems.filter((item) => item.group === id),
      })).filter((group) => group.items.length > 0);

      return (
        <div className="flex flex-col gap-2">
          {groups.map((group, index) => (
            <div
              key={group.id}
              className={cn(
                "flex flex-col gap-0.5",
                index > 0 && "pt-2 border-t border-border-01"
              )}
            >
              {group.items.map(renderNavItem)}
            </div>
          ))}
        </div>
      );
    }, [navVersion, navItems, renderNavItem]);

    const moreAgentsButton = useMemo(
      () => (
        <div data-testid="AppSidebar/more-agents">
          <SidebarTab
            leftIcon={
              folded || visibleAgents.length === 0
                ? ColorfulExploreAgents
                : ColorfulMoreAgents
            }
            href="/app/agents"
            folded={folded}
            transient={activeSidebarTab.isMoreAgents()}
            lowlight={!folded}
          >
            {visibleAgents.length === 0 ? "Explore Agents" : "More Agents"}
          </SidebarTab>
        </div>
      ),
      [folded, activeSidebarTab, visibleAgents]
    );
    const handleShowBuildIntro = useCallback(() => {
      setShowIntroAnimation(true);
    }, []);

    // The admin/curator entry is pinned here, directly above the user chip,
    // so it is reachable in one click instead of hidden inside the user menu.
    const settingsButton = useMemo(
      () => (
        <div className="flex flex-col gap-0.5">
          {/* v2 only — AdminEntryTab gates itself; v1 puts this in the user menu. */}
          <AdminEntryTab folded={folded} />
          <UserAvatarPopover
            folded={folded}
            onShowBuildIntro={
              isOmCraftEnabled ? handleShowBuildIntro : undefined
            }
          />
        </div>
      ),
      [folded, handleShowBuildIntro, isOmCraftEnabled]
    );

    return (
      <>
        <createWorkspaceModal.Provider>
          <CreateWorkspaceModal />
        </createWorkspaceModal.Provider>

        {showMoveCustomAgentModal && (
          <MoveCustomAgentChatModal
            onCancel={() => {
              setShowMoveCustomAgentModal(false);
              setPendingMoveChatSession(null);
              setPendingMoveWorkspaceId(null);
            }}
            onConfirm={async (doNotShowAgain: boolean) => {
              if (doNotShowAgain && typeof window !== "undefined") {
                window.localStorage.setItem(
                  LOCAL_STORAGE_KEYS.HIDE_MOVE_CUSTOM_AGENT_MODAL,
                  "true"
                );
              }
              const chat = pendingMoveChatSession;
              const target = pendingMoveWorkspaceId;
              setShowMoveCustomAgentModal(false);
              setPendingMoveChatSession(null);
              setPendingMoveWorkspaceId(null);
              if (chat && target != null) {
                try {
                  await performChatMove(target, chat);
                } catch (error) {
                  showErrorNotification(
                    "Failed to move chat. Please try again."
                  );
                }
              }
            }}
          />
        )}

        {/* Intro animation overlay */}
        <AnimatePresence>
          {showIntroAnimation && (
            <motion.div
              className="fixed inset-0 z-[9999]"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.5 }}
            >
              <BuildModeIntroBackground />
              <BuildModeIntroContent
                onClose={() => {
                  setShowIntroAnimation(false);
                  dismissBuildModeNotification();
                }}
                onTryBuildMode={() => {
                  setShowIntroAnimation(false);
                  dismissBuildModeNotification();
                  router.push(CRAFT_PATH);
                }}
              />
            </motion.div>
          )}
        </AnimatePresence>

        <SidebarWrapper folded={folded} onFoldClick={onFoldClick}>
          <SidebarBody
            scrollKey="app-sidebar"
            footer={settingsButton}
            actionButtons={actionButtons}
          >
            {/* When folded, show icons immediately without waiting for data */}
            {folded ? (
              <>{moreAgentsButton}</>
            ) : isLoadingDynamicContent ? null : (
              <>
                {/* Agents */}
                <DndContext
                  sensors={sensors}
                  collisionDetection={closestCenter}
                  onDragEnd={handleAgentDragEnd}
                >
                  <SidebarSection title="Agents">
                    <SortableContext
                      items={visibleAgentIds}
                      strategy={verticalListSortingStrategy}
                    >
                      {visibleAgents.map((visibleAgent) => (
                        <AgentButton
                          key={visibleAgent.id}
                          agent={visibleAgent}
                        />
                      ))}
                    </SortableContext>
                    {moreAgentsButton}
                  </SidebarSection>
                </DndContext>

                {/* Wrap Workspaces and Recents in a shared DndContext for chat-to-workspace drag */}
                <DndContext
                  sensors={sensors}
                  collisionDetection={pointerWithin}
                  modifiers={[
                    restrictToFirstScrollableAncestor,
                    restrictToVerticalAxis,
                  ]}
                  onDragEnd={handleChatWorkspaceDragEnd}
                >
                  {/* Scheduled runs (hidden when the user has no schedules) */}
                  <ScheduledSection />

                  {/* Recents */}
                  <RecentsSection chatSessions={chatSessions} />
                </DndContext>
              </>
            )}
          </SidebarBody>
        </SidebarWrapper>
      </>
    );
  }
);
MemoizedAppSidebarInner.displayName = "AppSidebar";

export default function AppSidebar() {
  const { folded, setFolded } = useAppSidebarContext();
  const { isMobile } = useScreenSize();

  if (!isMobile)
    return (
      <MemoizedAppSidebarInner
        folded={folded}
        onFoldClick={() => setFolded((prev) => !prev)}
      />
    );

  return (
    <>
      <div
        className={cn(
          "fixed inset-y-0 left-0 z-50 transition-transform duration-200",
          folded ? "-translate-x-full" : "translate-x-0"
        )}
      >
        <MemoizedAppSidebarInner
          folded={false}
          onFoldClick={() => setFolded(true)}
        />
      </div>

      {/* Hitbox to close the sidebar if anything outside of it is touched */}
      <div
        className={cn(
          "fixed inset-0 z-40 bg-mask-03 backdrop-blur-03 transition-opacity duration-200",
          folded
            ? "opacity-0 pointer-events-none"
            : "opacity-100 pointer-events-auto"
        )}
        onClick={() => setFolded(true)}
      />
    </>
  );
}
