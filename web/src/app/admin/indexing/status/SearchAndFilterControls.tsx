"use client";

import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { FilterComponent, FilterOptions } from "./FilterComponent";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import { Button } from "@opal/components";
import { SvgChevronDown, SvgChevronUp } from "@opal/icons";

interface SearchAndFilterControlsProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  hasExpandedSources: boolean;
  onExpandAll: () => void;
  onCollapseAll: () => void;
  filterOptions: FilterOptions;
  onFilterChange: (filterOptions: FilterOptions) => void;
  onClearFilters: () => void;
  hasActiveFilters: boolean;
  filterComponentRef: React.RefObject<{ resetFilters: () => void }>;
  resetPagination: () => void;
}

export function SearchAndFilterControls({
  searchQuery,
  onSearchChange,
  hasExpandedSources,
  onExpandAll,
  onCollapseAll,
  filterOptions,
  onFilterChange,
  onClearFilters,
  hasActiveFilters,
  filterComponentRef,
  resetPagination,
}: SearchAndFilterControlsProps) {
  const [localSearchValue, setLocalSearchValue] = useState(searchQuery);

  // Debounce the search query
  useEffect(() => {
    const timer = setTimeout(() => {
      resetPagination();
      onSearchChange(localSearchValue);
    }, 300);

    return () => clearTimeout(timer);
  }, [localSearchValue, onSearchChange, resetPagination]);

  // Sync with external searchQuery changes (e.g., when filters are cleared)
  useEffect(() => {
    setLocalSearchValue(searchQuery);
  }, [searchQuery]);

  return (
    <div className="flex flex-col gap-3 mb-4">
      {/* Search bar + actions row */}
      <div className="flex items-center gap-2">
        <div className="flex-1 max-w-md">
          <InputTypeIn
            placeholder="Search data sources..."
            type="text"
            value={localSearchValue}
            onChange={(event) => setLocalSearchValue(event.target.value)}
          />
        </div>

        <Button
          icon={hasExpandedSources ? SvgChevronUp : SvgChevronDown}
          prominence="secondary"
          onClick={hasExpandedSources ? onCollapseAll : onExpandAll}
        >
          {hasExpandedSources ? "Collapse All" : "Expand All"}
        </Button>

        <FilterComponent
          onFilterChange={onFilterChange}
          ref={filterComponentRef}
        />
      </div>

      {/* Active filter badges */}
      {hasActiveFilters && (
        <div className="flex flex-wrap items-center gap-1.5">
          {filterOptions.accessType &&
            filterOptions.accessType.length > 0 && (
              <Badge variant="secondary" className="px-2.5 py-1 text-xs rounded-full">
                Access: {filterOptions.accessType.join(", ")}
              </Badge>
            )}

          {filterOptions.lastStatus &&
            filterOptions.lastStatus.length > 0 && (
              <Badge variant="secondary" className="px-2.5 py-1 text-xs rounded-full">
                Status:{" "}
                {filterOptions.lastStatus
                  .map((s) => s.replace(/_/g, " "))
                  .join(", ")}
              </Badge>
            )}

          {filterOptions.docsCountFilter.operator &&
            filterOptions.docsCountFilter.value !== null && (
              <Badge variant="secondary" className="px-2.5 py-1 text-xs rounded-full">
                Docs {filterOptions.docsCountFilter.operator}{" "}
                {filterOptions.docsCountFilter.value}
              </Badge>
            )}

          {filterOptions.docsCountFilter.operator &&
            filterOptions.docsCountFilter.value === null && (
              <Badge variant="secondary" className="px-2.5 py-1 text-xs rounded-full">
                Docs {filterOptions.docsCountFilter.operator} any
              </Badge>
            )}

          <Badge
            variant="outline"
            className="px-2.5 py-1 text-xs rounded-full border-status-error-03 bg-status-error-01 hover:bg-status-error-02 cursor-pointer transition-colors"
            onClick={onClearFilters}
          >
            <span className="text-status-error-05">Clear filters</span>
          </Badge>
        </div>
      )}
    </div>
  );
}
