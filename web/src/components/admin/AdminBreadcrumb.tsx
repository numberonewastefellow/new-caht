"use client";

import { JSX } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { getSegmentLabel, isDynamicSegment } from "./adminNavItems";
import { SvgChevronRight } from "@opal/icons";
import Text from "@/refresh-components/texts/Text";

export interface AdminBreadcrumbProps {
  /** Override for the page title (last breadcrumb segment) */
  title?: string | JSX.Element;
  /** Optional element rendered at the far right (e.g., action buttons) */
  farRightElement?: JSX.Element;
}

export default function AdminBreadcrumb({
  title,
  farRightElement,
}: AdminBreadcrumbProps) {
  const pathname = usePathname();

  // Build breadcrumb segments from pathname
  // e.g. /admin/configuration/llm -> ["admin", "configuration", "llm"]
  const rawSegments = pathname
    .split("/")
    .filter(Boolean)
    .filter((seg) => !isDynamicSegment(seg));

  // Build cumulative paths for each segment
  const crumbs = rawSegments.map((segment, index) => {
    const path = "/" + rawSegments.slice(0, index + 1).join("/");
    const label = getSegmentLabel(segment);
    const isLast = index === rawSegments.length - 1;
    return { segment, path, label, isLast };
  });

  // Use title override for the last crumb if provided
  const lastCrumb = crumbs[crumbs.length - 1];
  if (lastCrumb && title && typeof title === "string") {
    lastCrumb.label = title;
  }

  return (
    <div className="w-full mb-6">
      {/* Breadcrumb trail */}
      <div className="flex items-center gap-1 mb-1">
        {crumbs.map((crumb, i) => (
          <span key={crumb.path} className="flex items-center gap-1">
            {i > 0 && (
              <SvgChevronRight className="w-3 h-3 stroke-text-03 flex-shrink-0" />
            )}
            {crumb.isLast ? (
              <Text as="span" mainUiBody text02>
                {crumb.label}
              </Text>
            ) : (
              <Link
                href={crumb.path as any}
                className="hover:underline"
              >
                <Text as="span" secondaryBody text03>
                  {crumb.label}
                </Text>
              </Link>
            )}
          </span>
        ))}
      </div>

      {/* Page heading + far right element */}
      <div className="flex items-center justify-between">
        <Text headingH2 aria-label="admin-page-title">
          {typeof title === "string" || title
            ? title
            : lastCrumb?.label ?? "Admin"}
        </Text>
        {farRightElement}
      </div>
    </div>
  );
}
