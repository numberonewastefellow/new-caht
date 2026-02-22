"use client";
import { use } from "react";

import { ErrorCallout } from "@/components/ErrorCallout";
import { refreshDocumentSets, useDocumentSets } from "../hooks";
import { useConnectorStatus, useUserGroups } from "@/lib/hooks";
import { ThreeDotsLoader } from "@/components/Loading";
import { AdminPageTitle } from "@/components/admin/Title";
import { SvgFolder } from "@opal/icons";
import BackButton from "@/refresh-components/buttons/BackButton";
import CardSection from "@/components/admin/CardSection";
import { DocumentSetCreationForm } from "../DocumentSetCreationForm";
import { useRouter } from "next/navigation";

function Main({ documentSetId }: { documentSetId: number }) {
  const router = useRouter();

  const {
    data: documentSets,
    isLoading: isDocumentSetsLoading,
    error: documentSetsError,
  } = useDocumentSets();

  const {
    data: ccPairs,
    isLoading: isCCPairsLoading,
    error: ccPairsError,
  } = useConnectorStatus();

  // EE only
  const { data: userGroups, isLoading: userGroupsIsLoading } = useUserGroups();

  if (isDocumentSetsLoading || isCCPairsLoading || userGroupsIsLoading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <ThreeDotsLoader />
      </div>
    );
  }

  if (documentSetsError || !documentSets) {
    return (
      <ErrorCallout
        errorTitle="Failed to fetch collections"
        errorMsg={documentSetsError}
      />
    );
  }

  if (ccPairsError || !ccPairs) {
    return (
      <ErrorCallout
        errorTitle="Failed to fetch Connectors"
        errorMsg={ccPairsError}
      />
    );
  }

  const documentSet = documentSets.find(
    (documentSet) => documentSet.id === documentSetId
  );
  if (!documentSet) {
    return (
      <ErrorCallout
        errorTitle="Collection not found"
        errorMsg={`Collection with id ${documentSetId} not found`}
      />
    );
  }

  return (
    <div>
      <AdminPageTitle
        icon={SvgFolder}
        title={documentSet.name}
        description="Edit this collection's name, description, and connected sources."
      />

      <CardSection>
        <DocumentSetCreationForm
          ccPairs={ccPairs}
          userGroups={userGroups}
          onClose={() => {
            refreshDocumentSets();
            router.push("/admin/documents/sets");
          }}
          existingDocumentSet={documentSet}
        />
      </CardSection>
    </div>
  );
}

export default function Page(props: {
  params: Promise<{ documentSetId: string }>;
}) {
  const params = use(props.params);
  const documentSetId = parseInt(params.documentSetId);

  return (
    <>
      <BackButton />

      <Main documentSetId={documentSetId} />
    </>
  );
}
