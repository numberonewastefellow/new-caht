"use client";

import { Team } from "@/lib/types";
import Text from "@/refresh-components/texts/Text";
import Button from "@/refresh-components/buttons/Button";
import IconButton from "@/refresh-components/buttons/IconButton";
import Popover from "@/refresh-components/Popover";
import LineItem from "@/refresh-components/buttons/LineItem";
import {
  SvgEdit,
  SvgMoreHorizontal,
  SvgSparkle,
  SvgTrash,
  SvgUserPlus,
  SvgUsers,
} from "@opal/icons";
import { useState } from "react";
import {
  TeamAvatar,
  UserAvatar,
  VisibilityBadge,
  TagChip,
  getKbCount,
  getMemberCount,
  getTeamOwner,
} from "./shared";

interface TeamDetailHeaderProps {
  team: Team;
  canManage: boolean;
  onAddMembers: () => void;
  onRename: () => void;
  onDelete: () => void;
}

export default function TeamDetailHeader({
  team,
  canManage,
  onAddMembers,
  onRename,
  onDelete,
}: TeamDetailHeaderProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const owner = getTeamOwner(team);

  return (
    <div className="rounded-16 border bg-background-tint-01 p-5">
      <div className="flex items-start gap-4">
        <TeamAvatar team={team} size={64} />

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Text headingH2 text05 className="truncate">
              {team.name}
            </Text>
            <VisibilityBadge isPublic={!!team.is_public} />
            {(team.tags ?? []).map((tag) => (
              <TagChip key={tag}>{tag}</TagChip>
            ))}
          </div>

          {team.description && (
            <Text
              as="p"
              mainContentBody
              text03
              className="mt-1.5 max-w-2xl"
            >
              {team.description}
            </Text>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2">
            {owner && (
              <div className="flex items-center gap-2">
                <UserAvatar
                  id={owner.id}
                  name={owner.name}
                  email={owner.email}
                  size={22}
                />
                <Text secondaryBody text03 className="text-sm">
                  Owned by
                </Text>
                <Text mainUiBody text04 className="text-sm">
                  {owner.name || owner.email}
                </Text>
              </div>
            )}
            <div className="flex items-center gap-1.5">
              <SvgUsers className="w-3.5 h-3.5 stroke-text-03" />
              <Text mainUiBody text04 className="text-sm">
                {getMemberCount(team)}
              </Text>
              <Text secondaryBody text03 className="text-sm">
                members
              </Text>
            </div>
            <div className="flex items-center gap-1.5">
              <SvgSparkle className="w-3.5 h-3.5 stroke-text-03" />
              <Text mainUiBody text04 className="text-sm">
                {getKbCount(team)}
              </Text>
              <Text secondaryBody text03 className="text-sm">
                KBs
              </Text>
            </div>
          </div>
        </div>

        {canManage && (
          <div className="flex items-center gap-2 shrink-0">
            <Button
              action
              secondary
              leftIcon={SvgUserPlus}
              onClick={onAddMembers}
            >
              Add members
            </Button>
            <Popover open={menuOpen} onOpenChange={setMenuOpen}>
              <Popover.Trigger asChild>
                <div>
                  <IconButton
                    main
                    tertiary
                    icon={SvgMoreHorizontal}
                    tooltip="More actions"
                  />
                </div>
              </Popover.Trigger>
              <Popover.Content align="end" side="bottom" width="md">
                <Popover.Menu>
                  <LineItem
                    icon={SvgEdit}
                    onClick={() => {
                      setMenuOpen(false);
                      onRename();
                    }}
                  >
                    Rename team
                  </LineItem>
                  {null}
                  <LineItem
                    danger
                    icon={SvgTrash}
                    onClick={() => {
                      setMenuOpen(false);
                      onDelete();
                    }}
                  >
                    Delete team
                  </LineItem>
                </Popover.Menu>
              </Popover.Content>
            </Popover>
          </div>
        )}
      </div>
    </div>
  );
}
