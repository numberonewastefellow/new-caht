"use client";

import { PersonasTable } from "./PersonaTable";
import { AdminPageTitle } from "@/components/admin/Title";
import { useAdminPersonas } from "@/hooks/useAdminPersonas";
import { ThreeDotsLoader } from "@/components/Loading";
import { ErrorCallout } from "@/components/ErrorCallout";
import { SvgOnyxOctagon, SvgPlus } from "@opal/icons";
import { useState, useEffect, useMemo } from "react";
import Pagination from "@/refresh-components/Pagination";
import Text from "@/refresh-components/texts/Text";
import Button from "@/refresh-components/buttons/Button";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import { Persona } from "./interfaces";

const PAGE_SIZE = 20;

function MainContent({
  personas,
  totalItems,
  currentPage,
  onPageChange,
  refreshPersonas,
}: {
  personas: Persona[];
  totalItems: number;
  currentPage: number;
  onPageChange: (page: number) => void;
  refreshPersonas: () => void;
}) {
  const customPersonas = personas.filter((persona) => !persona.builtin_persona);
  const totalPages = Math.ceil(totalItems / PAGE_SIZE);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    if (currentPage > totalPages && totalPages > 0) {
      onPageChange(totalPages);
    }
  }, [currentPage, totalPages, onPageChange]);

  const filteredPersonas = useMemo(() => {
    if (!searchQuery) return customPersonas;
    const q = searchQuery.toLowerCase();
    return customPersonas.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q)
    );
  }, [customPersonas, searchQuery]);

  return (
    <div className="flex flex-col gap-4">
      {/* Compact header */}
      <div className="flex flex-row items-center justify-between gap-4">
        <div className="flex flex-col">
          <Text as="p" secondaryBody text03>
            {totalItems} {totalItems === 1 ? "assistant" : "assistants"} managed by your organization.
          </Text>
        </div>
        <div className="flex flex-row items-center gap-2 flex-shrink-0">
          {totalItems > 6 && (
            <div className="w-[14rem]">
              <InputTypeIn
                placeholder="Search assistants..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                leftSearchIcon
              />
            </div>
          )}
          <Button href="/app/agents/create?admin=true" leftIcon={SvgPlus}>
            New Assistant
          </Button>
        </div>
      </div>

      {/* Card grid */}
      {filteredPersonas.length > 0 ? (
        <>
          <PersonasTable
            personas={filteredPersonas}
            refreshPersonas={refreshPersonas}
            currentPage={currentPage}
            pageSize={PAGE_SIZE}
          />
          {!searchQuery && totalPages > 1 && (
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              onPageChange={onPageChange}
            />
          )}
        </>
      ) : totalItems === 0 ? (
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
      ) : (
        <div className="flex flex-col items-center justify-center py-12">
          <Text as="p" secondaryBody text03>
            No assistants match &ldquo;{searchQuery}&rdquo;
          </Text>
        </div>
      )}
    </div>
  );
}

export default function Page() {
  const [currentPage, setCurrentPage] = useState(1);
  const { personas, totalItems, isLoading, error, refresh } = useAdminPersonas({
    pageNum: currentPage - 1,
    pageSize: PAGE_SIZE,
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
          personas={personas}
          totalItems={totalItems}
          currentPage={currentPage}
          onPageChange={setCurrentPage}
          refreshPersonas={refresh}
        />
      )}
    </>
  );
}
