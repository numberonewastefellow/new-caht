"use client";

import { AgentsTable } from "./AgentTable";
import { AdminPageTitle } from "@/components/admin/Title";
import { useAdminAgents } from "@/hooks/useAdminAgents";
import { ThreeDotsLoader } from "@/components/Loading";
import { ErrorCallout } from "@/components/ErrorCallout";
import { SvgOnyxOctagon, SvgPlus } from "@opal/icons";
import { useState, useEffect } from "react";
import Pagination from "@/refresh-components/Pagination";
import Text from "@/refresh-components/texts/Text";
import Button from "@/refresh-components/buttons/Button";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import { Agent } from "./interfaces";

const PAGE_SIZE = 20;

function MainContent({
  agents,
  totalItems,
  currentPage,
  onPageChange,
  refreshAgents,
  searchInput,
  onSearchChange,
  searchActive,
}: {
  agents: Agent[];
  totalItems: number;
  currentPage: number;
  onPageChange: (page: number) => void;
  refreshAgents: () => void;
  searchInput: string;
  onSearchChange: (value: string) => void;
  searchActive: boolean;
}) {
  const customAgents = agents.filter((agent) => !agent.builtin_agent);
  const totalPages = Math.ceil(totalItems / PAGE_SIZE);

  useEffect(() => {
    if (currentPage > totalPages && totalPages > 0) {
      onPageChange(totalPages);
    }
  }, [currentPage, totalPages, onPageChange]);

  return (
    <div className="flex flex-col gap-4">
      {/* Compact header */}
      <div className="flex flex-row items-center justify-between gap-4">
        <div className="flex flex-col">
          <Text as="p" secondaryBody text03>
            {totalItems} {totalItems === 1 ? "assistant" : "assistants"}{" "}
            {searchActive ? "found" : "managed by your organization"}.
          </Text>
        </div>
        <div className="flex flex-row items-center gap-2 flex-shrink-0">
          <div className="w-[14rem]">
            <InputTypeIn
              placeholder="Search assistants..."
              value={searchInput}
              onChange={(e) => onSearchChange(e.target.value)}
              leftSearchIcon
            />
          </div>
          <Button href="/app/agents/create?admin=true" leftIcon={SvgPlus}>
            New Assistant
          </Button>
        </div>
      </div>

      {/* Card grid */}
      {customAgents.length > 0 ? (
        <>
          <AgentsTable
            agents={customAgents}
            refreshAgents={refreshAgents}
            currentPage={currentPage}
            pageSize={PAGE_SIZE}
          />
          {totalPages > 1 && (
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              onPageChange={onPageChange}
            />
          )}
        </>
      ) : searchActive ? (
        <div className="flex flex-col items-center justify-center py-12">
          <Text as="p" secondaryBody text03>
            No assistants match &ldquo;{searchInput}&rdquo;
          </Text>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 gap-4">
          <div className="w-16 h-16 rounded-full bg-background-neutral-02 flex items-center justify-center">
            <SvgOnyxOctagon className="w-8 h-8 text-text-03" />
          </div>
          <div className="text-center">
            <Text as="p" mainContentBody className="font-medium mb-1">
              No assistants yet
            </Text>
            <Text as="p" secondaryBody text03>
              Create your first assistant to build custom AI experiences.
            </Text>
          </div>
          <Button href="/app/agents/create?admin=true" leftIcon={SvgPlus}>
            Create Your First Assistant
          </Button>
        </div>
      )}
    </div>
  );
}

export default function Page() {
  const [currentPage, setCurrentPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  // Debounce the search input so we don't fire a request per keystroke.
  useEffect(() => {
    const handle = setTimeout(() => setDebouncedQuery(searchInput.trim()), 300);
    return () => clearTimeout(handle);
  }, [searchInput]);

  // Reset to the first page whenever the (debounced) search term changes.
  useEffect(() => {
    setCurrentPage(1);
  }, [debouncedQuery]);

  // Server-side search across ALL assistants (matches name OR description),
  // not just the current page. keepPreviousData (in the hook) avoids the list
  // unmounting between fetches so the search box keeps focus.
  const { agents, totalItems, isLoading, error, refresh } = useAdminAgents({
    pageNum: currentPage - 1,
    pageSize: PAGE_SIZE,
    searchQuery: debouncedQuery,
  });

  return (
    <>
      <AdminPageTitle icon={SvgOnyxOctagon} title="Assistants" />

      {isLoading && <ThreeDotsLoader />}

      {error && (
        <ErrorCallout
          errorTitle="Failed to load assistants"
          errorMsg={
            error?.info?.message ||
            error?.info?.detail ||
            "An unknown error occurred"
          }
        />
      )}

      {!isLoading && !error && (
        <MainContent
          agents={agents}
          totalItems={totalItems}
          currentPage={currentPage}
          onPageChange={setCurrentPage}
          refreshAgents={refresh}
          searchInput={searchInput}
          onSearchChange={setSearchInput}
          searchActive={debouncedQuery.length > 0}
        />
      )}
    </>
  );
}
