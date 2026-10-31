"use client";

import { memo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import type { Route } from "next";
import SidebarSection from "@/sections/sidebar/SidebarSection";
import SidebarTab from "@/refresh-components/buttons/SidebarTab";
import IconButton from "@/refresh-components/buttons/IconButton";
import useAppFocus from "@/hooks/useAppFocus";
import { usePulseSidebar } from "@/hooks/useSchedules";
import { noProp } from "@/lib/utils";
import { chatHref, triggerHref } from "@/lib/schedules/api";
import { formatRelative } from "@/lib/schedules/format";
import { scheduleDot } from "@/lib/schedules/status";
import type { PulseSidebarItem } from "@/lib/schedules/interfaces";
import { StatusDot } from "@/sections/schedules/StatusPill";
import { SvgExternalLink, SvgPlus } from "@opal/icons";

const COLLAPSED_KEY = "sidebar-scheduled-collapsed";

/** "2 h ago" -> "2h", "50 min ago" -> "50m" (compact for the sidebar). */
function compactAgo(iso: string | null): string {
  if (!iso) return "";
  const rel = formatRelative(iso);
  if (rel === "just now") return "now";
  return rel
    .replace(" ago", "")
    .replace(" min", "m")
    .replace(" h", "h")
    .replace(" d", "d");
}

interface ScheduledRowProps {
  item: PulseSidebarItem;
  active: boolean;
}

const ScheduledRow = memo(function ScheduledRow({
  item,
  active,
}: ScheduledRowProps) {
  const router = useRouter();
  const href = item.latest_chat_session_id
    ? chatHref(item.latest_chat_session_id)
    : triggerHref(item.kind, item.trigger_id);
  const ago = compactAgo(item.last_run_at);

  return (
    <SidebarTab
      href={href}
      transient={active}
      rightChildren={
        <>
          {ago && (
            <span className="text-xs text-text-02 whitespace-nowrap group-hover/SidebarTab:hidden">
              {ago}
            </span>
          )}
          <div className="hidden group-hover/SidebarTab:flex">
            <IconButton
              icon={SvgExternalLink}
              internal
              tooltip="Open schedule"
              aria-label="Open schedule"
              onClick={noProp(() =>
                router.push(triggerHref(item.kind, item.trigger_id) as Route)
              )}
            />
          </div>
        </>
      }
    >
      <div
        className="flex items-center gap-2 min-w-0 w-full"
        title={
          item.latest_chat_session_id
            ? `${item.name} — opens the latest run`
            : item.name
        }
      >
        <span className="w-4 flex items-center justify-center flex-shrink-0">
          <StatusDot dot={scheduleDot(item)} />
        </span>
        <span className="truncate text-sm sidebar-tab-text-defaulted">
          {item.name}
        </span>
      </div>
    </SidebarTab>
  );
});

/** Collapsible section listing the user's schedules and webhooks. */
export default function ScheduledSection() {
  const { items } = usePulseSidebar();
  const router = useRouter();
  const pathname = usePathname();
  const appFocus = useAppFocus();
  // Rows only render client-side (SWR data), so reading storage here is safe.
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return (
        typeof window !== "undefined" &&
        window.localStorage.getItem(COLLAPSED_KEY) === "true"
      );
    } catch {
      return false;
    }
  });

  function toggle() {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        window.localStorage.setItem(COLLAPSED_KEY, String(next));
      } catch {
        // ignore
      }
      return next;
    });
  }

  if (items.length === 0) return null;

  const currentChatId = appFocus.isChat() ? appFocus.getId() : null;

  return (
    <SidebarSection
      title="Pulse runs"
      collapsible
      collapsed={collapsed}
      onToggle={toggle}
      action={
        <IconButton
          icon={SvgPlus}
          internal
          tooltip="New schedule"
          aria-label="New schedule"
          onClick={noProp(() => router.push("/app/schedules?new=1" as Route))}
        />
      }
    >
      {items.map((item) => (
        <ScheduledRow
          key={item.trigger_id}
          item={item}
          active={
            (!!currentChatId &&
              currentChatId === item.latest_chat_session_id) ||
            pathname === triggerHref(item.kind, item.trigger_id)
          }
        />
      ))}
    </SidebarSection>
  );
}
