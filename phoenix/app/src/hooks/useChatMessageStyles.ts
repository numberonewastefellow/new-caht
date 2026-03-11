import { useMemo } from "react";

import type { ViewStyleProps } from "@phoenix/components/core/types";
import { ChatRoleMap } from "@phoenix/constants/generativeConstants";

/**
 * VirtualAI enterprise chat message styling.
 * Uses the VirtualAI gradient palette for role differentiation:
 * - System: Violet (#7c3aed) — authoritative
 * - User: Pink (#e8449a) — human input
 * - AI/Assistant: Indigo (#4338ca) — machine output
 * - Tool/Function: Magenta (#c026d3) — tool execution
 */
export function useChatMessageStyles(
  role: string
): Pick<ViewStyleProps, "backgroundColor" | "borderColor"> {
  return useMemo<ViewStyleProps>(() => {
    const normalizedRole = role.toLowerCase();
    if (ChatRoleMap.user.includes(normalizedRole)) {
      return {
        backgroundColor: "gray-200",
        borderColor: "gray-400",
      };
    } else if (ChatRoleMap.ai.includes(normalizedRole)) {
      return {
        backgroundColor: "indigo-100",
        borderColor: "indigo-700",
      };
    } else if (ChatRoleMap.system.includes(normalizedRole)) {
      return {
        backgroundColor: "purple-100",
        borderColor: "purple-700",
      };
    } else if (["function", "tool"].includes(normalizedRole)) {
      return {
        backgroundColor: "magenta-100",
        borderColor: "magenta-700",
      };
    }
    return {
      backgroundColor: "gray-100",
      borderColor: "gray-500",
    };
  }, [role]);
}
