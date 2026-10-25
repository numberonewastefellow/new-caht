"use client";

import React from "react";
import { TableHead } from "@/components/ui/table";
import { cn } from "@/lib/utils";

/** Table header cell using theme tokens (overrides the base neutral colors). */
export default function Th({
  className,
  children,
}: {
  className?: string;
  children?: React.ReactNode;
}) {
  return (
    <TableHead
      className={cn(
        "h-10 px-3.5 text-[11.5px] uppercase tracking-wide font-semibold",
        className
      )}
      style={{ color: "var(--text-03)" }}
    >
      {children}
    </TableHead>
  );
}
