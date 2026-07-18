"use client";

import React, { useState, useMemo, useCallback } from "react";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import CommandMenu, {
  useCommandMenuContext,
} from "@/refresh-components/commandmenu/CommandMenu";
import { useWorkspaces } from "@/lib/hooks/useWorkspaces";
import { useCreateModal } from "@/refresh-components/contexts/ModalContext";
import CreateWorkspaceModal from "@/components/modals/CreateWorkspaceModal";
import {
  formatDisplayTime,
  highlightMatch,
} from "@/sections/sidebar/chatSearchUtils";
import { useSettingsContext } from "@/providers/SettingsProvider";
import { useCurrentAgent } from "@/hooks/useAgents";
import Text from "@/refresh-components/texts/Text";
import {
  useChatSearchOptimistic,
  FilterableChat,
} from "./useChatSearchOptimistic";
import {
  SvgEditBig,
  SvgFolder,
  SvgFolderPlus,
  SvgBubbleText,
  SvgArrowUpDown,
  SvgKeystroke,
} from "@opal/icons";
import TextSeparator from "@/refresh-components/TextSeparator";

/**
 * Dynamic footer that shows contextual action labels based on highlighted item type
 */
function DynamicFooter() {
  const { highlightedItemType } = useCommandMenuContext();

  // "Show all" for filters, "Open" for everything else (items, actions, or no highlight)
  const actionLabel = highlightedItemType === "filter" ? "Show all" : "Open";

  return (
    <CommandMenu.Footer
      leftActions={
        <>
          <CommandMenu.FooterAction icon={SvgArrowUpDown} label="Select" />
          <CommandMenu.FooterAction icon={SvgKeystroke} label={actionLabel} />
        </>
      }
    />
  );
}

interface ChatSearchCommandMenuProps {
  trigger: React.ReactNode;
}

interface FilterableWorkspace {
  id: number;
  label: string;
  description: string | null;
  time: string;
}

export default function ChatSearchCommandMenu({
  trigger,
}: ChatSearchCommandMenuProps) {
  const [open, setOpen] = useState(false);
  const [searchValue, setSearchValue] = useState("");
  const [activeFilter, setActiveFilter] = useState<
    "all" | "chats" | "workspaces"
  >("all");
  const [initialWorkspaceName, setInitialWorkspaceName] = useState<
    string | undefined
  >();
  const router = useRouter();

  // Data hooks
  const { workspaces } = useWorkspaces();
  const combinedSettings = useSettingsContext();
  const currentAgent = useCurrentAgent();
  const createWorkspaceModal = useCreateModal();

  // Constants for preview limits
  const PREVIEW_CHATS_LIMIT = 4;
  const PREVIEW_PROJECTS_LIMIT = 3;

  // Determine if we should enable optimistic search (when searching or viewing chats filter)
  const shouldUseOptimisticSearch =
    searchValue.trim().length > 0 || activeFilter === "chats";

  // Use optimistic search hook for chat sessions (includes fallback from useChatSessions + useWorkspaces)
  const {
    results: filteredChats,
    isSearching,
    hasMore,
    isLoadingMore,
    sentinelRef,
  } = useChatSearchOptimistic({
    searchQuery: searchValue,
    enabled: shouldUseOptimisticSearch,
  });

  // Transform and filter workspaces (sorted by latest first)
  const filteredWorkspaces = useMemo<FilterableWorkspace[]>(() => {
    const workspaceList = workspaces
      .map((workspace) => ({
        id: workspace.id,
        label: workspace.name,
        description: workspace.description,
        time: workspace.created_at,
      }))
      .sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime());

    if (!searchValue.trim()) return workspaceList;

    const term = searchValue.toLowerCase();
    return workspaceList.filter(
      (workspace) =>
        workspace.label.toLowerCase().includes(term) ||
        workspace.description?.toLowerCase().includes(term)
    );
  }, [workspaces, searchValue]);

  // Compute displayed items based on filter state
  const displayedChats = useMemo(() => {
    if (activeFilter === "all" && !searchValue.trim()) {
      return filteredChats.slice(0, PREVIEW_CHATS_LIMIT);
    }
    return filteredChats;
  }, [filteredChats, activeFilter, searchValue]);

  const displayedWorkspaces = useMemo(() => {
    if (activeFilter === "all" && !searchValue.trim()) {
      return filteredWorkspaces.slice(0, PREVIEW_PROJECTS_LIMIT);
    }
    return filteredWorkspaces;
  }, [filteredWorkspaces, activeFilter, searchValue]);

  // Header filters for showing active filter as a chip
  const headerFilters = useMemo(() => {
    if (activeFilter === "chats") {
      return [{ id: "chats", label: "Sessions" }];
    }
    if (activeFilter === "workspaces") {
      return [{ id: "workspaces", label: "Workspaces" }];
    }
    return [];
  }, [activeFilter]);

  const handleFilterRemove = useCallback(() => {
    setActiveFilter("all");
  }, []);

  // Navigation handlers
  const handleNewSession = useCallback(() => {
    const href =
      combinedSettings?.settings?.disable_default_assistant && currentAgent
        ? `/app?assistantId=${currentAgent.id}`
        : "/app";
    router.push(href as Route);
    setOpen(false);
  }, [router, combinedSettings, currentAgent]);

  const handleChatSelect = useCallback(
    (chatId: string) => {
      router.push(`/chat?chatId=${chatId}` as Route);
      setOpen(false);
    },
    [router]
  );

  const handleWorkspaceSelect = useCallback(
    (workspaceId: number) => {
      router.push(`/chat?workspaceId=${workspaceId}` as Route);
      setOpen(false);
    },
    [router]
  );

  const handleNewWorkspace = useCallback(
    (initialName?: string) => {
      setInitialWorkspaceName(initialName);
      setOpen(false);
      createWorkspaceModal.toggle(true);
    },
    [createWorkspaceModal]
  );

  const handleOpenChange = useCallback((newOpen: boolean) => {
    setOpen(newOpen);
    if (!newOpen) {
      setSearchValue("");
      setActiveFilter("all");
    }
  }, []);

  const handleEmptyBackspace = useCallback(() => {
    if (activeFilter !== "all") {
      // Remove active filter, return to root menu
      setActiveFilter("all");
    } else {
      // No filter active, close the menu
      setOpen(false);
    }
  }, [activeFilter]);

  const hasSearchValue = searchValue.trim().length > 0;

  return (
    <>
      <div aria-label="Open chat search" onClick={() => setOpen(true)}>
        {trigger}
      </div>

      <CommandMenu open={open} onOpenChange={handleOpenChange}>
        <CommandMenu.Content>
          <CommandMenu.Header
            placeholder="Search chat sessions, workspaces..."
            value={searchValue}
            onValueChange={setSearchValue}
            filters={headerFilters}
            onFilterRemove={handleFilterRemove}
            onClose={() => setOpen(false)}
            onEmptyBackspace={handleEmptyBackspace}
          />

          <CommandMenu.List
            emptyMessage={
              hasSearchValue ? "No results found" : "No chats or workspaces yet"
            }
          >
            {/* New Session action - always visible in "all" filter, even during search */}
            {activeFilter === "all" && (
              <CommandMenu.Action
                value="new-session"
                icon={SvgEditBig}
                onSelect={handleNewSession}
                defaultHighlight={!hasSearchValue}
              >
                New Session
              </CommandMenu.Action>
            )}

            {/* Recent Sessions section - show if filter is 'all' or 'chats' */}
            {(activeFilter === "all" || activeFilter === "chats") &&
              displayedChats.length > 0 && (
                <>
                  {searchValue.trim().length === 0 && (
                    <CommandMenu.Filter
                      value="recent-sessions"
                      onSelect={() => setActiveFilter("chats")}
                      isApplied={
                        activeFilter === "chats" ||
                        filteredChats.length <= PREVIEW_CHATS_LIMIT
                      }
                    >
                      {activeFilter === "chats" ? "Recent" : "Recent Sessions"}
                    </CommandMenu.Filter>
                  )}
                  {displayedChats.map((chat) => (
                    <CommandMenu.Item
                      key={chat.id}
                      value={`chat-${chat.id}`}
                      icon={SvgBubbleText}
                      rightContent={({ isHighlighted }) =>
                        isHighlighted ? (
                          <Text figureKeystroke text02>
                            ↵
                          </Text>
                        ) : (
                          <Text secondaryBody text03>
                            {formatDisplayTime(chat.time)}
                          </Text>
                        )
                      }
                      onSelect={() => handleChatSelect(chat.id)}
                    >
                      {highlightMatch(chat.label, searchValue)}
                    </CommandMenu.Item>
                  ))}
                  {/* Infinite scroll sentinel and loading indicator for chats */}
                  {activeFilter === "chats" && hasMore && (
                    <div ref={sentinelRef} className="h-1" aria-hidden="true" />
                  )}
                  {activeFilter === "chats" &&
                    (isLoadingMore || isSearching) && (
                      <div className="flex justify-center items-center py-3">
                        <div className="h-5 w-5 animate-spin rounded-full border-2 border-solid border-text-04 border-t-text-02" />
                      </div>
                    )}
                </>
              )}

            {/* Workspaces section - show if filter is 'all' or 'workspaces' */}
            {(activeFilter === "all" || activeFilter === "workspaces") && (
              <>
                <CommandMenu.Filter
                  value="workspaces"
                  onSelect={() => setActiveFilter("workspaces")}
                  isApplied={
                    activeFilter === "workspaces" ||
                    filteredWorkspaces.length <= PREVIEW_PROJECTS_LIMIT
                  }
                >
                  Workspaces
                </CommandMenu.Filter>
                {/* New Workspace action - shown after Workspaces filter when no search term */}
                {!hasSearchValue && activeFilter === "all" && (
                  <CommandMenu.Action
                    value="new-workspace"
                    icon={SvgFolderPlus}
                    onSelect={() => handleNewWorkspace()}
                  >
                    New Workspace
                  </CommandMenu.Action>
                )}
                {displayedWorkspaces.map((workspace) => (
                  <CommandMenu.Item
                    key={workspace.id}
                    value={`workspace-${workspace.id}`}
                    icon={SvgFolder}
                    rightContent={({ isHighlighted }) =>
                      isHighlighted ? (
                        <Text figureKeystroke text02>
                          ↵
                        </Text>
                      ) : (
                        <Text secondaryBody text03>
                          {formatDisplayTime(workspace.time)}
                        </Text>
                      )
                    }
                    onSelect={() => handleWorkspaceSelect(workspace.id)}
                  >
                    {highlightMatch(workspace.label, searchValue)}
                  </CommandMenu.Item>
                ))}
              </>
            )}

            {/* Create New Workspace with search term - shown at bottom when searching */}
            {hasSearchValue &&
              (activeFilter === "all" || activeFilter === "workspaces") && (
                <CommandMenu.Action
                  value="create-workspace-with-name"
                  icon={SvgFolderPlus}
                  onSelect={() => handleNewWorkspace(searchValue.trim())}
                >
                  <>
                    Create New Workspace "
                    <span className="text-text-05">{searchValue.trim()}</span>"
                  </>
                </CommandMenu.Action>
              )}

            {/* No more results separator - shown when no results for the active filter */}
            {((activeFilter === "chats" && displayedChats.length === 0) ||
              (activeFilter === "workspaces" && displayedWorkspaces.length === 0) ||
              (activeFilter === "all" &&
                displayedChats.length === 0 &&
                displayedWorkspaces.length === 0)) && (
              <TextSeparator text="No more results" className="mt-auto mb-2" />
            )}
          </CommandMenu.List>

          <DynamicFooter />
        </CommandMenu.Content>
      </CommandMenu>

      {/* Workspace creation modal */}
      <createWorkspaceModal.Provider>
        <CreateWorkspaceModal initialWorkspaceName={initialWorkspaceName} />
      </createWorkspaceModal.Provider>
    </>
  );
}
