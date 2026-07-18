"use client";

import React from "react";
import { SEARCH_TOOL_ID } from "@/app/app/components/tools/constants";
import { ToolSnapshot } from "@/lib/tools/interfaces";
import { getIconForAction } from "@/app/app/services/actionUtils";
import { ToolAuthStatus } from "@/lib/hooks/useToolOAuthStatus";
import LineItem from "@/refresh-components/buttons/LineItem";
import SimpleTooltip from "@/refresh-components/SimpleTooltip";
import IconButton from "@/refresh-components/buttons/IconButton";
import Switch from "@/refresh-components/inputs/Switch";
import { Button } from "@opal/components";
import { cn, noProp } from "@/lib/utils";
import type { IconProps } from "@opal/types";
import { SvgChevronRight, SvgKey, SvgSettings } from "@opal/icons";
import { useWorkspacesContext } from "@/providers/WorkspacesContext";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import EnabledCount from "@/refresh-components/EnabledCount";
import { Section } from "@/layouts/general-layouts";

export interface ActionItemProps {
  tool?: ToolSnapshot;
  Icon?: React.FunctionComponent<IconProps>;
  /** Override the default icon with a colorful variant */
  colorfulIcon?: React.FunctionComponent<IconProps>;
  label?: string;
  disabled: boolean;
  isForced: boolean;
  isUnavailable?: boolean;
  unavailableReason?: string;
  showAdminConfigure?: boolean;
  adminConfigureHref?: string;
  adminConfigureTooltip?: string;
  onToggle: () => void;
  onForceToggle: () => void;
  onSourceManagementOpen?: () => void;
  hasNoConnectors?: boolean;
  hasNoKnowledgeSources?: boolean;
  toolAuthStatus?: ToolAuthStatus;
  onOAuthAuthenticate?: () => void;
  onClose?: () => void;
  // Source counts for internal search tool
  sourceCounts?: { enabled: number; total: number };
}

export default function ActionLineItem({
  tool,
  Icon: ProvidedIcon,
  colorfulIcon: ColorfulIcon,
  label: providedLabel,
  disabled,
  isForced,
  isUnavailable = false,
  unavailableReason,
  showAdminConfigure = false,
  adminConfigureHref,
  adminConfigureTooltip = "Configure",
  onToggle,
  onForceToggle,
  onSourceManagementOpen,
  hasNoConnectors = false,
  hasNoKnowledgeSources = false,
  toolAuthStatus,
  onOAuthAuthenticate,
  onClose,
  sourceCounts,
}: ActionItemProps) {
  const router = useRouter();
  const { currentWorkspaceId } = useWorkspacesContext();

  const Icon = ColorfulIcon ?? (tool ? getIconForAction(tool) : ProvidedIcon!);
  const toolName = tool?.name || providedLabel || "";

  let label = tool ? tool.display_name || tool.name : providedLabel!;
  if (!!currentWorkspaceId && tool?.in_code_tool_id === SEARCH_TOOL_ID) {
    label = "Workspace Search";
  }

  const isSearchToolWithNoConnectors =
    !currentWorkspaceId &&
    tool?.in_code_tool_id === SEARCH_TOOL_ID &&
    hasNoConnectors;

  const isSearchToolWithNoKnowledgeSources =
    !currentWorkspaceId &&
    tool?.in_code_tool_id === SEARCH_TOOL_ID &&
    hasNoKnowledgeSources;

  const isSearchToolAndNotInWorkspace =
    tool?.in_code_tool_id === SEARCH_TOOL_ID && !currentWorkspaceId;

  // Show source count when: internal search is pinned, has some (but not all) sources enabled
  const shouldShowSourceCount =
    isSearchToolAndNotInWorkspace &&
    !isSearchToolWithNoConnectors &&
    isForced &&
    sourceCounts &&
    sourceCounts.enabled > 0 &&
    sourceCounts.enabled < sourceCounts.total;

  const tooltipText = isSearchToolWithNoKnowledgeSources
    ? "No knowledge sources are available. Contact your admin to add a knowledge source to this agent."
    : isUnavailable
      ? unavailableReason
      : tool?.description;

  return (
    <SimpleTooltip tooltip={tooltipText} className="max-w-[30rem]">
      <div data-testid={`tool-option-${toolName}`}>
        <LineItem
          onClick={() => {
            if (
              isSearchToolWithNoConnectors ||
              isSearchToolWithNoKnowledgeSources
            )
              return;
            if (isUnavailable) {
              if (isForced) onForceToggle();
              return;
            }
            if (disabled) onToggle();
            onForceToggle();
            if (isSearchToolAndNotInWorkspace && !isForced)
              onSourceManagementOpen?.();
            else onClose?.();
          }}
          selected={isForced}
          strikethrough={
            isSearchToolWithNoConnectors ||
            isSearchToolWithNoKnowledgeSources ||
            isUnavailable
          }
          muted={disabled && !isUnavailable && !isSearchToolWithNoConnectors && !isSearchToolWithNoKnowledgeSources}
          icon={Icon}
          rightChildren={
            <Section gap={0.25} flexDirection="row">
              {!isUnavailable && tool?.oauth_config_id && toolAuthStatus && (
                <Button
                  icon={({ className }) => (
                    <SvgKey
                      className={cn(
                        className,
                        "stroke-yellow-500 hover:stroke-yellow-600"
                      )}
                    />
                  )}
                  onClick={noProp(() => {
                    if (
                      !toolAuthStatus.hasToken ||
                      toolAuthStatus.isTokenExpired
                    ) {
                      onOAuthAuthenticate?.();
                    }
                  })}
                />
              )}

              {!isSearchToolWithNoConnectors && !isUnavailable && !shouldShowSourceCount && (
                <SimpleTooltip tooltip={disabled ? "Enable tool" : "Disable tool"}>
                  <span onClick={noProp(() => {})} className="flex items-center">
                    <Switch
                      checked={!disabled}
                      onCheckedChange={() => onToggle()}
                    />
                  </span>
                </SimpleTooltip>
              )}

              {isUnavailable && showAdminConfigure && adminConfigureHref && (
                <Button
                  icon={SvgSettings}
                  onClick={noProp(() => {
                    router.push(adminConfigureHref as Route);
                    onClose?.();
                  })}
                  prominence="tertiary"
                  size="sm"
                  tooltip={adminConfigureTooltip}
                />
              )}

              {/* Source count + toggle for internal search */}
              {shouldShowSourceCount && (
                <span className="flex items-center gap-1.5 whitespace-nowrap">
                  <EnabledCount
                    enabledCount={sourceCounts.enabled}
                    totalCount={sourceCounts.total}
                  />
                  <SimpleTooltip tooltip={disabled ? "Enable tool" : "Disable tool"}>
                    <span onClick={noProp(() => {})} className="flex items-center">
                      <Switch
                        checked={!disabled}
                        onCheckedChange={() => onToggle()}
                      />
                    </span>
                  </SimpleTooltip>
                </span>
              )}

              {isSearchToolAndNotInWorkspace &&
                !isSearchToolWithNoKnowledgeSources && (
                  <IconButton
                    icon={
                      isSearchToolWithNoConnectors
                        ? SvgSettings
                        : SvgChevronRight
                    }
                    onClick={noProp(() => {
                      if (isSearchToolWithNoConnectors)
                        router.push("/admin/add-connector");
                      else onSourceManagementOpen?.();
                    })}
                    internal
                    className={cn(
                      isSearchToolWithNoConnectors &&
                        "invisible group-hover/LineItem:visible"
                    )}
                    tooltip={
                      isSearchToolWithNoConnectors
                        ? "Add Connectors"
                        : "Configure Connectors"
                    }
                  />
                )}
            </Section>
          }
        >
          {label}
        </LineItem>
      </div>
    </SimpleTooltip>
  );
}
