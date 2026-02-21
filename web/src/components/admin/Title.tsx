"use client";

import { JSX } from "react";
import type { IconProps } from "@opal/types";
import AdminBreadcrumb from "./AdminBreadcrumb";

export interface AdminPageTitleProps {
  icon: React.FunctionComponent<IconProps> | React.ReactNode;
  title: string | JSX.Element;
  farRightElement?: JSX.Element;
  includeDivider?: boolean;
}

/**
 * AdminPageTitle — backward-compatible wrapper that now renders breadcrumbs.
 *
 * The `icon` prop is accepted for API compatibility but no longer rendered
 * (icons are shown in the top bar navigation instead).
 * The `title` prop is used as the page heading and last breadcrumb segment.
 * The `includeDivider` prop is accepted but ignored (breadcrumbs handle spacing).
 */
export function AdminPageTitle({
  icon: _icon,
  title,
  farRightElement,
  includeDivider: _includeDivider,
}: AdminPageTitleProps) {
  const titleStr = typeof title === "string" ? title : undefined;

  return (
    <AdminBreadcrumb
      title={titleStr ?? title}
      farRightElement={farRightElement}
    />
  );
}
