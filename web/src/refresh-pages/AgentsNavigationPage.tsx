"use client";

import { useMemo, useState, useRef, useEffect, useCallback } from "react";
import AgentCard from "@/sections/cards/AgentCard";
import { useUser } from "@/providers/UserProvider";
import { checkUserOwnsAssistant as checkUserOwnsAgent } from "@/lib/agents";
import { useAgents } from "@/hooks/useAgents";
import { MinimalPersonaSnapshot } from "@/app/admin/assistants/interfaces";
import Text from "@/refresh-components/texts/Text";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import * as SettingsLayouts from "@/layouts/settings-layouts";
import Tabs from "@/refresh-components/Tabs";
import FilterButton from "@/refresh-components/buttons/FilterButton";
import Popover, { PopoverMenu } from "@/refresh-components/Popover";
import LineItem from "@/refresh-components/buttons/LineItem";
import Button from "@/refresh-components/buttons/Button";
import {
  SEARCH_TOOL_ID,
  IMAGE_GENERATION_TOOL_ID,
  OPEN_URL_TOOL_ID,
  OPEN_URL_TOOL_NAME,
  WEB_SEARCH_TOOL_ID,
  SYSTEM_TOOL_ICONS,
} from "@/app/app/components/tools/constants";
import {
  SvgActions,
  SvgCheck,
  SvgOnyxOctagon,
  SvgPlus,
  SvgUser,
} from "@opal/icons";
import useOnMount from "@/hooks/useOnMount";

const PAGE_SIZE = 24;

interface AgentsSectionProps {
  title: string;
  description?: string;
  agents: MinimalPersonaSnapshot[];
  visibleCount: number;
}

function AgentsSection({
  title,
  description,
  agents,
  visibleCount,
}: AgentsSectionProps) {
  const sorted = useMemo(
    () => [...agents].sort((a, b) => b.id - a.id),
    [agents]
  );
  const visible = sorted.slice(0, visibleCount);

  if (agents.length === 0) return null;

  return (
    <div className="flex flex-col gap-3">
      <div>
        <Text as="p" headingH3>
          {title}
        </Text>
        {description && (
          <Text as="p" secondaryBody text03>
            {description}
          </Text>
        )}
      </div>
      <div className="w-full grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
        {visible.map((agent) => (
          <AgentCard key={agent.id} agent={agent} />
        ))}
      </div>
    </div>
  );
}

export default function AgentsNavigationPage() {
  const { agents } = useAgents();
  const [creatorFilterOpen, setCreatorFilterOpen] = useState(false);
  const [actionsFilterOpen, setActionsFilterOpen] = useState(false);
  const { user } = useUser();
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState<"all" | "your">("all");
  const [selectedCreatorIds, setSelectedCreatorIds] = useState<Set<string>>(
    new Set()
  );
  const [selectedActionIds, setSelectedActionIds] = useState<Set<number>>(
    new Set()
  );
  const [selectedMcpServerIds, setSelectedMcpServerIds] = useState<
    Set<number>
  >(new Set());
  const [creatorSearchQuery, setCreatorSearchQuery] = useState("");
  const [actionsSearchQuery, setActionsSearchQuery] = useState("");
  const [mcpServersMap, setMcpServersMap] = useState<
    Map<number, { id: number; name: string }>
  >(new Map());
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Pagination: how many agents to show
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  useOnMount(() => {
    searchInputRef.current?.focus();
  });

  // Fetch all MCP servers used by agents
  useEffect(() => {
    const fetchMCPServers = async () => {
      const serverIds = new Set<number>();
      agents.forEach((agent) => {
        agent.tools.forEach((tool) => {
          if (
            tool.mcp_server_id !== null &&
            tool.mcp_server_id !== undefined
          ) {
            serverIds.add(tool.mcp_server_id);
          }
        });
      });

      if (serverIds.size === 0) return;

      const serversMap = new Map<number, { id: number; name: string }>();

      for (const serverId of Array.from(serverIds)) {
        try {
          const agentWithServer = agents.find((agent) =>
            agent.tools.some((tool) => tool.mcp_server_id === serverId)
          );

          if (agentWithServer) {
            const response = await fetch(
              `/api/mcp/servers/persona/${agentWithServer.id}`
            );
            if (response.ok) {
              const data = await response.json();
              const server = data.mcp_servers?.find(
                (s: any) => s.id === serverId
              );
              if (server) {
                serversMap.set(serverId, {
                  id: server.id,
                  name: server.name,
                });
              }
            }
          }
        } catch (error) {
          console.error(`Error fetching MCP server ${serverId}:`, error);
        }
      }

      setMcpServersMap(serversMap);
    };

    fetchMCPServers();
  }, [agents]);

  const uniqueCreators = useMemo(() => {
    const creatorsMap = new Map<string, { id: string; email: string }>();
    agents.forEach((agent) => {
      if (agent.owner) {
        creatorsMap.set(agent.owner.id, agent.owner);
      }
    });

    let creators = Array.from(creatorsMap.values()).sort((a, b) =>
      a.email.localeCompare(b.email)
    );

    if (user) {
      const hasCurrentUser = creators.some((c) => c.id === user.id);

      if (!hasCurrentUser) {
        creators = [{ id: user.id, email: user.email }, ...creators];
      } else {
        creators = creators.sort((a, b) => {
          if (a.id === user.id) return -1;
          if (b.id === user.id) return 1;
          return 0;
        });
      }
    }

    return creators;
  }, [agents, user]);

  const filteredCreators = useMemo(() => {
    if (!creatorSearchQuery) return uniqueCreators;

    return uniqueCreators.filter((creator) =>
      creator.email.toLowerCase().includes(creatorSearchQuery.toLowerCase())
    );
  }, [uniqueCreators, creatorSearchQuery]);

  const uniqueActions = useMemo(() => {
    const actionsMap = new Map<
      number,
      {
        id: number;
        name: string;
        display_name: string;
        mcp_server_id?: number | null;
      }
    >();
    agents.forEach((agent) => {
      agent.tools.forEach((tool) => {
        if (
          tool.in_code_tool_id === OPEN_URL_TOOL_ID ||
          tool.name === OPEN_URL_TOOL_ID ||
          tool.name === OPEN_URL_TOOL_NAME
        ) {
          return;
        }
        actionsMap.set(tool.id, {
          id: tool.id,
          name: tool.name,
          display_name: tool.display_name,
          mcp_server_id: tool.mcp_server_id,
        });
      });
    });

    const systemToolIds = [
      SEARCH_TOOL_ID,
      IMAGE_GENERATION_TOOL_ID,
      WEB_SEARCH_TOOL_ID,
    ];

    const allActions = Array.from(actionsMap.values());
    const systemTools = allActions.filter((action) =>
      systemToolIds.includes(action.name)
    );
    const otherTools = allActions.filter(
      (action) => !systemToolIds.includes(action.name)
    );

    systemTools.sort((a, b) => a.display_name.localeCompare(b.display_name));
    otherTools.sort((a, b) => a.display_name.localeCompare(b.display_name));

    const mcpGroupsMap = new Map<number, typeof allActions>();
    const nonMcpSystemTools: typeof systemTools = [];
    const nonMcpOtherTools: typeof otherTools = [];

    systemTools.forEach((tool) => {
      if (tool.mcp_server_id !== null && tool.mcp_server_id !== undefined) {
        const group = mcpGroupsMap.get(tool.mcp_server_id) || [];
        group.push(tool);
        mcpGroupsMap.set(tool.mcp_server_id, group);
      } else {
        nonMcpSystemTools.push(tool);
      }
    });

    otherTools.forEach((tool) => {
      if (tool.mcp_server_id !== null && tool.mcp_server_id !== undefined) {
        const group = mcpGroupsMap.get(tool.mcp_server_id) || [];
        group.push(tool);
        mcpGroupsMap.set(tool.mcp_server_id, group);
      } else {
        nonMcpOtherTools.push(tool);
      }
    });

    type ActionItem =
      | {
          type: "tool";
          id: number;
          name: string;
          display_name: string;
          mcp_server_id?: number | null;
        }
      | {
          type: "mcp_group";
          mcp_server_id: number;
          server_name: string;
          tools: Array<{ id: number; name: string; display_name: string }>;
        };

    const mcpGroupItems: ActionItem[] = Array.from(
      mcpGroupsMap.entries()
    ).map(([serverId, tools]) => {
      const serverInfo = mcpServersMap.get(serverId);
      return {
        type: "mcp_group" as const,
        mcp_server_id: serverId,
        server_name: serverInfo?.name || `MCP Server ${serverId}`,
        tools: tools.map((t) => ({
          id: t.id,
          name: t.name,
          display_name: t.display_name,
        })),
      };
    });

    const nonMcpSystemToolItems: ActionItem[] = nonMcpSystemTools.map(
      (tool) => ({ type: "tool" as const, ...tool })
    );
    const nonMcpOtherToolItems: ActionItem[] = nonMcpOtherTools.map(
      (tool) => ({
        type: "tool" as const,
        ...tool,
      })
    );

    return [
      ...nonMcpSystemToolItems,
      ...mcpGroupItems,
      ...nonMcpOtherToolItems,
    ];
  }, [agents, mcpServersMap]);

  const filteredActions = useMemo(() => {
    if (!actionsSearchQuery) return uniqueActions;

    const query = actionsSearchQuery.toLowerCase();
    return uniqueActions.filter((action) => {
      if (action.type === "tool") {
        return action.display_name.toLowerCase().includes(query);
      } else {
        return action.tools.some((tool) =>
          tool.display_name.toLowerCase().includes(query)
        );
      }
    });
  }, [uniqueActions, actionsSearchQuery]);

  const memoizedCurrentlyVisibleAgents = useMemo(() => {
    return agents.filter((agent) => {
      const nameMatches = agent.name
        .toLowerCase()
        .includes(searchQuery.toLowerCase());
      const labelMatches = agent.labels?.some((label) =>
        label.name.toLowerCase().includes(searchQuery.toLowerCase())
      );

      const mineFilter =
        activeTab === "your" ? checkUserOwnsAgent(user, agent) : true;
      const isNotUnifiedAgent = agent.id !== 0;

      const creatorFilter =
        selectedCreatorIds.size === 0 ||
        (agent.owner && selectedCreatorIds.has(agent.owner.id));

      const actionsFilter =
        (selectedActionIds.size === 0 && selectedMcpServerIds.size === 0) ||
        agent.tools.some(
          (tool) =>
            selectedActionIds.has(tool.id) ||
            (tool.mcp_server_id !== null &&
              tool.mcp_server_id !== undefined &&
              selectedMcpServerIds.has(tool.mcp_server_id))
        );

      return (
        (nameMatches || labelMatches) &&
        mineFilter &&
        isNotUnifiedAgent &&
        creatorFilter &&
        actionsFilter
      );
    });
  }, [
    agents,
    searchQuery,
    activeTab,
    user,
    selectedCreatorIds,
    selectedActionIds,
    selectedMcpServerIds,
  ]);

  // Reset pagination when filters change
  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [
    searchQuery,
    activeTab,
    selectedCreatorIds,
    selectedActionIds,
    selectedMcpServerIds,
  ]);

  const featuredAgents = useMemo(
    () =>
      memoizedCurrentlyVisibleAgents.filter(
        (agent) => agent.is_default_persona
      ),
    [memoizedCurrentlyVisibleAgents]
  );
  const allAgents = useMemo(
    () =>
      memoizedCurrentlyVisibleAgents.filter(
        (agent) => !agent.is_default_persona
      ),
    [memoizedCurrentlyVisibleAgents]
  );

  const agentCount = featuredAgents.length + allAgents.length;
  const hasMore =
    featuredAgents.length + allAgents.length > visibleCount;

  const handleShowMore = useCallback(() => {
    setVisibleCount((prev) => prev + PAGE_SIZE);
  }, []);

  const creatorFilterButtonText = useMemo(() => {
    if (selectedCreatorIds.size === 0) {
      return "Everyone";
    } else if (selectedCreatorIds.size === 1) {
      const selectedId = Array.from(selectedCreatorIds)[0];
      const creator = uniqueCreators.find((c) => c.id === selectedId);
      return `By ${creator?.email}` || "Everyone";
    } else {
      return `${selectedCreatorIds.size} people`;
    }
  }, [selectedCreatorIds, uniqueCreators]);

  const actionsFilterButtonText = useMemo(() => {
    const totalSelected = selectedActionIds.size + selectedMcpServerIds.size;

    if (totalSelected === 0) {
      return "All Actions";
    } else if (totalSelected === 1) {
      if (selectedActionIds.size === 1) {
        const selectedId = Array.from(selectedActionIds)[0];
        for (const action of uniqueActions) {
          if (action.type === "tool" && action.id === selectedId) {
            return action.display_name;
          }
        }
      }

      if (selectedMcpServerIds.size === 1) {
        const selectedServerId = Array.from(selectedMcpServerIds)[0];
        for (const action of uniqueActions) {
          if (
            action.type === "mcp_group" &&
            action.mcp_server_id === selectedServerId
          ) {
            return action.server_name;
          }
        }
      }

      return "All Actions";
    } else {
      return `${totalSelected} selected`;
    }
  }, [selectedActionIds, selectedMcpServerIds, uniqueActions]);

  // Compute how many from each section to show given visibleCount
  const featuredVisible = Math.min(featuredAgents.length, visibleCount);
  const allVisible = Math.max(0, visibleCount - featuredAgents.length);

  return (
    <SettingsLayouts.Root
      width="lg"
      data-testid="AgentsPage/container"
      aria-label="Agents Page"
    >
      <SettingsLayouts.Header
        icon={SvgOnyxOctagon}
        title="Agents & Assistants"
        description="Customize AI behavior and knowledge for you and your team's use cases."
        rightChildren={
          <div data-testid="AgentsPage/new-agent-button">
            <Button href="/app/agents/create" leftIcon={SvgPlus}>
              New Agent
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-2">
          <div className="flex flex-row items-center gap-2">
            <div className="flex-[2]">
              <InputTypeIn
                ref={searchInputRef}
                placeholder="Search agents..."
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                leftSearchIcon
              />
            </div>
            <div className="flex-1">
              <Tabs
                value={activeTab}
                onValueChange={(value) =>
                  setActiveTab(value as "all" | "your")
                }
              >
                <Tabs.List>
                  <Tabs.Trigger value="all">All Agents</Tabs.Trigger>
                  <Tabs.Trigger value="your">Your Agents</Tabs.Trigger>
                </Tabs.List>
              </Tabs>
            </div>
          </div>
          <div className="flex flex-row gap-2">
            <Popover
              open={creatorFilterOpen}
              onOpenChange={setCreatorFilterOpen}
            >
              <Popover.Trigger asChild>
                <FilterButton
                  leftIcon={SvgUser}
                  active={selectedCreatorIds.size > 0}
                  transient={creatorFilterOpen}
                  onClear={() => setSelectedCreatorIds(new Set())}
                >
                  {creatorFilterButtonText}
                </FilterButton>
              </Popover.Trigger>
              <Popover.Content align="start">
                <PopoverMenu>
                  {[
                    <InputTypeIn
                      key="created-by"
                      placeholder="Created by..."
                      variant="internal"
                      leftSearchIcon
                      value={creatorSearchQuery}
                      onChange={(e) =>
                        setCreatorSearchQuery(e.target.value)
                      }
                    />,
                    ...filteredCreators.flatMap((creator, index) => {
                      const isSelected = selectedCreatorIds.has(creator.id);
                      const isCurrentUser = user && creator.id === user.id;

                      const nextCreator = filteredCreators[index + 1];
                      const nextIsCurrentUser =
                        user && nextCreator && nextCreator.id === user.id;
                      const needsSeparator =
                        isCurrentUser && nextCreator && !nextIsCurrentUser;

                      const icon = isCurrentUser
                        ? SvgUser
                        : isSelected
                          ? SvgCheck
                          : () => null;

                      const lineItem = (
                        <LineItem
                          key={creator.id}
                          icon={icon}
                          selected={isSelected}
                          emphasized
                          onClick={() => {
                            setSelectedCreatorIds((prev) => {
                              const newSet = new Set(prev);
                              if (newSet.has(creator.id)) {
                                newSet.delete(creator.id);
                              } else {
                                newSet.add(creator.id);
                              }
                              return newSet;
                            });
                          }}
                        >
                          {creator.email}
                        </LineItem>
                      );

                      return needsSeparator ? [lineItem, null] : [lineItem];
                    }),
                  ]}
                </PopoverMenu>
              </Popover.Content>
            </Popover>
            <Popover
              open={actionsFilterOpen}
              onOpenChange={setActionsFilterOpen}
            >
              <Popover.Trigger asChild>
                <FilterButton
                  leftIcon={SvgActions}
                  transient={actionsFilterOpen}
                  active={
                    selectedActionIds.size > 0 ||
                    selectedMcpServerIds.size > 0
                  }
                  onClear={() => {
                    setSelectedActionIds(new Set());
                    setSelectedMcpServerIds(new Set());
                  }}
                >
                  {actionsFilterButtonText}
                </FilterButton>
              </Popover.Trigger>
              <Popover.Content align="start">
                <PopoverMenu>
                  {[
                    <InputTypeIn
                      key="actions"
                      placeholder="Filter actions..."
                      variant="internal"
                      leftSearchIcon
                      value={actionsSearchQuery}
                      onChange={(e) =>
                        setActionsSearchQuery(e.target.value)
                      }
                    />,
                    ...filteredActions.flatMap((action, index) => {
                      if (action.type === "tool") {
                        const isSelected = selectedActionIds.has(action.id);
                        const systemIcon = SYSTEM_TOOL_ICONS[action.name];
                        const isSystemTool = !!systemIcon;

                        const nextAction = filteredActions[index + 1];
                        const nextIsSystemTool =
                          nextAction && nextAction.type === "tool"
                            ? !!SYSTEM_TOOL_ICONS[nextAction.name]
                            : false;
                        const needsSeparator =
                          isSystemTool && nextAction && !nextIsSystemTool;

                        const icon = systemIcon ? systemIcon : SvgActions;

                        const lineItem = (
                          <LineItem
                            key={action.id}
                            icon={icon}
                            selected={isSelected}
                            emphasized
                            onClick={() => {
                              setSelectedActionIds((prev) => {
                                const newSet = new Set(prev);
                                if (newSet.has(action.id)) {
                                  newSet.delete(action.id);
                                } else {
                                  newSet.add(action.id);
                                }
                                return newSet;
                              });
                            }}
                          >
                            {action.display_name}
                          </LineItem>
                        );

                        return needsSeparator
                          ? [lineItem, null]
                          : [lineItem];
                      } else {
                        const groupKey = `mcp-group-${action.mcp_server_id}`;
                        const isSelected = selectedMcpServerIds.has(
                          action.mcp_server_id
                        );

                        const lineItem = (
                          <LineItem
                            key={groupKey}
                            icon={SvgActions}
                            selected={isSelected}
                            emphasized
                            onClick={() => {
                              setSelectedMcpServerIds((prev) => {
                                const newSet = new Set(prev);
                                if (newSet.has(action.mcp_server_id)) {
                                  newSet.delete(action.mcp_server_id);
                                } else {
                                  newSet.add(action.mcp_server_id);
                                }
                                return newSet;
                              });
                            }}
                          >
                            {action.server_name}
                          </LineItem>
                        );

                        return [lineItem];
                      }
                    }),
                  ]}
                </PopoverMenu>
              </Popover.Content>
            </Popover>
          </div>
        </div>
      </SettingsLayouts.Header>

      {/* Agents List */}
      <SettingsLayouts.Body>
        {agentCount === 0 ? (
          <Text
            as="p"
            className="w-full h-full flex flex-col items-center justify-center py-12"
            text03
          >
            No Agents found
          </Text>
        ) : (
          <div className="flex flex-col gap-8">
            <AgentsSection
              title="Featured Agents"
              description="Curated by your team"
              agents={featuredAgents}
              visibleCount={featuredVisible}
            />
            <AgentsSection
              title="All Agents"
              agents={allAgents}
              visibleCount={allVisible}
            />

            {/* Result count + Show More */}
            <div className="flex flex-col items-center gap-3 py-2">
              {hasMore && (
                <Button tertiary onClick={handleShowMore}>
                  Show more agents
                </Button>
              )}
              <Text as="p" secondaryBody text02>
                Showing{" "}
                {Math.min(visibleCount, agentCount)} of {agentCount}{" "}
                {agentCount === 1 ? "agent" : "agents"}
              </Text>
            </div>
          </div>
        )}
      </SettingsLayouts.Body>
    </SettingsLayouts.Root>
  );
}
