"use client";

import { JSX } from "react";
import type { IconProps } from "@opal/types";
import AdminBreadcrumb from "./AdminBreadcrumb";

export interface AdminPageTitleProps {
  icon: React.FunctionComponent<IconProps> | React.ReactNode;
  title: string | JSX.Element;
  farRightElement?: JSX.Element;
  includeDivider?: boolean;
  /** Optional subtitle text below the title */
  description?: string;
}

/**
 * AdminPageTitle — backward-compatible wrapper that now renders breadcrumbs
 * with a colorful page icon.
 */
export function AdminPageTitle({
  icon,
  title,
  farRightElement,
  includeDivider: _includeDivider,
  description,
}: AdminPageTitleProps) {
  const titleStr = typeof title === "string" ? title : undefined;

  return (
    <AdminBreadcrumb
      title={titleStr ?? title}
      icon={icon}
      description={description}
      farRightElement={farRightElement}
    />
  );
}
