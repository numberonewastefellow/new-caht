"use client";

import { ThreeDotsLoader } from "@/components/Loading";
import { PageSelector } from "@/components/PageSelector";
import { InfoIcon } from "@/components/icons/icons";
import { SvgFolder } from "@opal/icons";
import {
  Table,
  TableHead,
  TableRow,
  TableBody,
  TableCell,
} from "@/components/ui/table";
import Text from "@/components/ui/text";
import RefreshText from "@/refresh-components/texts/Text";
import Title from "@/components/ui/title";
import Separator from "@/refresh-components/Separator";
import CardSection from "@/components/admin/CardSection";
import { DocumentSetSummary } from "@/lib/types";
import { useState } from "react";
import { useDocumentSets } from "./hooks";
import { ConnectorTitle } from "@/components/admin/connectors/ConnectorTitle";
import { deleteDocumentSet } from "./lib";
import { toast } from "@/hooks/useToast";
import { AdminPageTitle } from "@/components/admin/Title";
import {
  FiAlertTriangle,
  FiCheckCircle,
  FiClock,
  FiEdit2,
  FiLock,
  FiUnlock,
} from "react-icons/fi";
import { DeleteButton } from "@/components/DeleteButton";
import { useRouter } from "next/navigation";
import { TableHeader } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import CreateButton from "@/refresh-components/buttons/CreateButton";
import { SourceIcon } from "@/components/SourceIcon";
import Link from "next/link";

const numToDisplay = 50;

// Component to display federated connectors with consistent styling
const FederatedConnectorTitle = ({
  federatedConnector,
  showMetadata = true,
  isLink = true,
}: {
  federatedConnector: any;
  showMetadata?: boolean;
  isLink?: boolean;
}) => {
  const sourceType = federatedConnector.source.replace(/^federated_/, "");

  const mainSectionClassName = "text-text-05 flex w-fit items-center";
  const mainDisplay = (
    <>
      <SourceIcon sourceType={sourceType as any} iconSize={16} />
      <div className="ml-1 my-auto text-xs font-medium truncate">
        {federatedConnector.name}
      </div>
      <Badge variant="outline" className="text-xs ml-2">
        Federated
      </Badge>
    </>
  );

  return (
    <div className="my-auto max-w-full">
      {isLink ? (
        <Link
          className={mainSectionClassName}
          href={`/admin/federated/${federatedConnector.id}`}
        >
          {mainDisplay}
        </Link>
      ) : (
        <div className={mainSectionClassName}>{mainDisplay}</div>
      )}
      {showMetadata && Object.keys(federatedConnector.entities).length > 0 && (
        <div className="text-[10px] mt-0.5 text-text-02">
          {Object.entries(federatedConnector.entities)
            .filter(
              ([_, value]) =>
                value &&
                (Array.isArray(value) ? value.length > 0 : String(value).trim())
            )
            .map(([key, value]) => (
              <div key={key} className="truncate">
                <i>{key}:</i>{" "}
                {Array.isArray(value) ? value.join(", ") : String(value)}
              </div>
            ))}
        </div>
      )}
    </div>
  );
};

const EditRow = ({
  documentSet,
  isEditable,
}: {
  documentSet: DocumentSetSummary;
  isEditable: boolean;
}) => {
  const router = useRouter();

  if (!isEditable) {
    return (
      <div className="text-text-04 font-medium my-auto p-1">
        {documentSet.name}
      </div>
    );
  }

  return (
    <div className="relative flex">
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              className={`
              text-text-05 font-medium my-auto p-1 rounded-08 transition-colors flex items-center select-none
              ${documentSet.is_up_to_date ? "cursor-pointer hover:bg-background-tint-02" : "cursor-default opacity-70"}
            `}
              style={{ wordBreak: "normal", overflowWrap: "break-word" }}
              onClick={() => {
                if (documentSet.is_up_to_date) {
                  router.push(`/admin/documents/sets/${documentSet.id}`);
                }
              }}
            >
              <FiEdit2 className="mr-2 flex-shrink-0 w-3.5 h-3.5" />
              <span className="font-medium">{documentSet.name}</span>
            </div>
          </TooltipTrigger>
          {!documentSet.is_up_to_date && (
            <TooltipContent width="max-w-sm">
              <div className="flex break-words break-keep whitespace-pre-wrap items-start">
                <InfoIcon className="mr-2 mt-0.5" />
                Cannot update while syncing! Wait for the sync to finish, then
                try again.
              </div>
            </TooltipContent>
          )}
        </Tooltip>
      </TooltipProvider>
    </div>
  );
};

interface DocumentFeedbackTableProps {
  documentSets: DocumentSetSummary[];
  refresh: () => void;
  refreshEditable: () => void;
  editableDocumentSets: DocumentSetSummary[];
}

const DocumentSetTable = ({
  documentSets,
  editableDocumentSets,
  refresh,
  refreshEditable,
}: DocumentFeedbackTableProps) => {
  const [page, setPage] = useState(1);

  // sort by name for consistent ordering
  documentSets.sort((a, b) => {
    if (a.name < b.name) {
      return -1;
    } else if (a.name > b.name) {
      return 1;
    } else {
      return 0;
    }
  });

  const sortedDocumentSets = [
    ...editableDocumentSets,
    ...documentSets.filter(
      (ds) => !editableDocumentSets.some((eds) => eds.id === ds.id)
    ),
  ];

  return (
    <CardSection>
      <div className="flex items-center justify-between mb-4">
        <Title className="!mb-0">Existing Collections</Title>
        <RefreshText as="span" secondaryBody text03>
          {sortedDocumentSets.length} collection{sortedDocumentSets.length !== 1 ? "s" : ""}
        </RefreshText>
      </div>
      <Table className="overflow-visible">
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Sources</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Visibility</TableHead>
            <TableHead className="w-16 text-center">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedDocumentSets
            .slice((page - 1) * numToDisplay, page * numToDisplay)
            .map((documentSet) => {
              const isEditable = editableDocumentSets.some(
                (eds) => eds.id === documentSet.id
              );
              return (
                <TableRow key={documentSet.id}>
                  <TableCell className="whitespace-normal break-all">
                    <div className="flex gap-x-1 text-emphasis">
                      <EditRow
                        documentSet={documentSet}
                        isEditable={isEditable}
                      />
                    </div>
                  </TableCell>
                  <TableCell>
                    <div>
                      {/* Regular Connectors */}
                      {documentSet.cc_pair_summaries.map(
                        (ccPairSummary, ind) => {
                          return (
                            <div
                              className={
                                ind !== documentSet.cc_pair_summaries.length - 1
                                  ? "mb-3"
                                  : ""
                              }
                              key={ccPairSummary.id}
                            >
                              <div className="text-text-05 flex w-fit items-center">
                                <SourceIcon
                                  sourceType={ccPairSummary.source}
                                  iconSize={16}
                                />
                                <div className="ml-1 my-auto text-xs font-medium truncate">
                                  {ccPairSummary.name || "Unnamed"}
                                </div>
                              </div>
                            </div>
                          );
                        }
                      )}

                      {/* Federated Connectors */}
                      {documentSet.federated_connector_summaries &&
                        documentSet.federated_connector_summaries.length >
                          0 && (
                          <>
                            {documentSet.cc_pair_summaries.length > 0 && (
                              <div className="mb-3" />
                            )}
                            {documentSet.federated_connector_summaries.map(
                              (federatedConnector, ind) => {
                                return (
                                  <div
                                    className={
                                      ind !==
                                      documentSet.federated_connector_summaries
                                        .length -
                                        1
                                        ? "mb-3"
                                        : ""
                                    }
                                    key={`federated-${federatedConnector.id}`}
                                  >
                                    <FederatedConnectorTitle
                                      federatedConnector={federatedConnector}
                                      showMetadata={true}
                                    />
                                  </div>
                                );
                              }
                            )}
                          </>
                        )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {documentSet.is_up_to_date ? (
                      <Badge variant="success" icon={FiCheckCircle}>
                        Up to Date
                      </Badge>
                    ) : documentSet.cc_pair_summaries.length > 0 ||
                      (documentSet.federated_connector_summaries &&
                        documentSet.federated_connector_summaries.length >
                          0) ? (
                      <Badge variant="in_progress" icon={FiClock}>
                        Syncing
                      </Badge>
                    ) : (
                      <Badge variant="destructive" icon={FiAlertTriangle}>
                        Deleting
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    {documentSet.is_public ? (
                      <Badge
                        variant={isEditable ? "success" : "default"}
                        icon={FiUnlock}
                      >
                        Public
                      </Badge>
                    ) : (
                      <Badge
                        variant={isEditable ? "private" : "default"}
                        icon={FiLock}
                      >
                        Private
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-center">
                    {isEditable ? (
                      <DeleteButton
                        onClick={async () => {
                          const response = await deleteDocumentSet(
                            documentSet.id
                          );
                          if (response.ok) {
                            toast.success(
                              `Collection "${documentSet.name}" scheduled for deletion`
                            );
                          } else {
                            const errorMsg = (await response.json()).detail;
                            toast.error(
                              `Failed to schedule collection for deletion - ${errorMsg}`
                            );
                          }
                          refresh();
                          refreshEditable();
                        }}
                      />
                    ) : (
                      <span className="text-text-02">—</span>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
        </TableBody>
      </Table>

      <div className="mt-4 flex">
        <div className="mx-auto">
          <PageSelector
            totalPages={Math.ceil(sortedDocumentSets.length / numToDisplay)}
            currentPage={page}
            onPageChange={(newPage) => setPage(newPage)}
          />
        </div>
      </div>
    </CardSection>
  );
};

const Main = () => {
  const {
    data: documentSets,
    isLoading: isDocumentSetsLoading,
    error: documentSetsError,
    refreshDocumentSets,
  } = useDocumentSets();

  const {
    data: editableDocumentSets,
    isLoading: isEditableDocumentSetsLoading,
    error: editableDocumentSetsError,
    refreshDocumentSets: refreshEditableDocumentSets,
  } = useDocumentSets(true);

  if (isDocumentSetsLoading || isEditableDocumentSetsLoading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <ThreeDotsLoader />
      </div>
    );
  }

  if (documentSetsError || !documentSets) {
    return <div>Error: {documentSetsError}</div>;
  }

  if (editableDocumentSetsError || !editableDocumentSets) {
    return <div>Error: {editableDocumentSetsError}</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <CreateButton href="/admin/documents/sets/new">
          New Collection
        </CreateButton>
        {documentSets.length > 0 && (
          <RefreshText as="span" secondaryBody text03>
            {documentSets.length} total collection{documentSets.length !== 1 ? "s" : ""}
          </RefreshText>
        )}
      </div>

      {documentSets.length > 0 && (
        <DocumentSetTable
          documentSets={documentSets}
          editableDocumentSets={editableDocumentSets}
          refresh={refreshDocumentSets}
          refreshEditable={refreshEditableDocumentSets}
        />
      )}

      {documentSets.length === 0 && (
        <CardSection className="text-center py-12">
          <SvgFolder className="w-12 h-12 mx-auto mb-3 text-text-02" />
          <RefreshText as="p" mainUiMuted text03>
            No collections yet. Create your first collection to group knowledge sources.
          </RefreshText>
        </CardSection>
      )}
    </div>
  );
};

const Page = () => {
  return (
    <>
      <AdminPageTitle
        icon={SvgFolder}
        title="Collections"
        description="Group related knowledge sources into curated collections for scoped AI retrieval."
      />

      <Main />
    </>
  );
};

export default Page;
