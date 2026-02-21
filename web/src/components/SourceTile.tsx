import { SourceIcon } from "@/components/SourceIcon";
import Link from "next/link";
import type { Route } from "next";
import { SourceMetadata } from "@/lib/search/interfaces";
import React from "react";
import Text from "@/refresh-components/texts/Text";

interface SourceTileProps {
  sourceMetadata: SourceMetadata;
  preSelect?: boolean;
  navigationUrl: string;
  hasExistingSlackCredentials: boolean;
  /** Render as a larger featured card (for Popular section) */
  featured?: boolean;
}

export default function SourceTile({
  sourceMetadata,
  preSelect,
  navigationUrl,
  featured,
}: SourceTileProps) {
  if (featured) {
    return (
      <Link
        className={`flex items-center gap-3 p-4 rounded-lg w-full
          cursor-pointer bg-background-tint-00 border border-transparent
          hover:border-virtualai-accent hover:bg-virtualai-accent-glow
          hover:shadow-sm transition-all
          ${preSelect ? "subtle-pulse" : ""}`}
        href={navigationUrl as Route}
      >
        <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-background-tint-02 flex items-center justify-center">
          <SourceIcon sourceType={sourceMetadata.internalName} iconSize={24} />
        </div>
        <div className="flex-1 min-w-0">
          <Text as="p" mainUiAction className="truncate">
            {sourceMetadata.displayName}
          </Text>
          <Text as="p" secondaryBody text03 className="text-xs truncate">
            {sourceMetadata.category}
          </Text>
        </div>
      </Link>
    );
  }

  return (
    <Link
      className={`flex flex-col items-center justify-center p-4 rounded-lg
        w-full cursor-pointer bg-background-tint-00 border border-transparent
        hover:border-virtualai-accent hover:bg-virtualai-accent-glow
        hover:shadow-sm transition-all relative
        ${preSelect ? "subtle-pulse" : ""}`}
      href={navigationUrl as Route}
    >
      <SourceIcon sourceType={sourceMetadata.internalName} iconSize={24} />
      <Text as="p" className="pt-2 text-center truncate w-full">
        {sourceMetadata.displayName}
      </Text>
    </Link>
  );
}
