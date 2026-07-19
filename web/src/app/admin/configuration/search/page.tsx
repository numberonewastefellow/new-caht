"use client";

import { ThreeDotsLoader } from "@/components/Loading";
import { AdminPageTitle } from "@/components/admin/Title";
import { errorHandlingFetcher } from "@/lib/fetcher";
import Title from "@/components/ui/title";
import Button from "@/refresh-components/buttons/Button";
import useSWR from "swr";
import {
  HostedEmbeddingModel,
  CloudEmbeddingModel,
  getFormattedProviderName,
} from "@/components/embedding/interfaces";
import { SavedSearchSettings } from "@/app/admin/embeddings/interfaces";
import UpgradingPage from "./UpgradingPage";
import { useContext } from "react";
import { SettingsContext } from "@/providers/SettingsProvider";
import CardSection from "@/components/admin/CardSection";
import { ErrorCallout } from "@/components/ErrorCallout";
import { useToastFromQuery } from "@/hooks/useToast";
import { SvgSearch, SvgSettings } from "@opal/icons";
import QueryExpansionSettings from "./QueryExpansionSettings";

export interface EmbeddingDetails {
  api_key: string;
  custom_config: any;
  default_model_id?: number;
  name: string;
}

function StatusBadge({ enabled }: { enabled: boolean }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
        enabled
          ? "bg-green-500/10 text-green-600 dark:text-green-400"
          : "bg-text-02/10 text-text-03"
      }`}
    >
      {enabled ? "Enabled" : "Disabled"}
    </span>
  );
}

function DetailRow({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-baseline justify-between py-2.5 px-4 border-b border-border-01 last:border-b-0">
      <span className="text-sm text-text-03">{label}</span>
      <span className="text-sm font-medium text-text-05">{value}</span>
    </div>
  );
}

function Main() {
  const settings = useContext(SettingsContext);
  useToastFromQuery({
    "search-settings": {
      message: `Changed search settings successfully`,
      type: "success",
    },
  });
  const {
    data: currentEmbeddingModel,
    isLoading: isLoadingCurrentModel,
    error: currentEmbeddingModelError,
  } = useSWR<CloudEmbeddingModel | HostedEmbeddingModel | null>(
    "/api/search-settings/get-current-search-settings",
    errorHandlingFetcher,
    { refreshInterval: 5000 }
  );

  const { data: searchSettings, isLoading: isLoadingSearchSettings } =
    useSWR<SavedSearchSettings | null>(
      "/api/search-settings/get-current-search-settings",
      errorHandlingFetcher,
      { refreshInterval: 5000 }
    );

  const {
    data: futureEmbeddingModel,
    isLoading: isLoadingFutureModel,
    error: futureEmbeddingModelError,
  } = useSWR<CloudEmbeddingModel | HostedEmbeddingModel | null>(
    "/api/search-settings/get-secondary-search-settings",
    errorHandlingFetcher,
    { refreshInterval: 5000 }
  );

  if (
    isLoadingCurrentModel ||
    isLoadingFutureModel ||
    isLoadingSearchSettings
  ) {
    return <ThreeDotsLoader />;
  }

  if (
    currentEmbeddingModelError ||
    !currentEmbeddingModel ||
    futureEmbeddingModelError
  ) {
    return <ErrorCallout errorTitle="Failed to fetch embedding model status" />;
  }

  return (
    <div className="space-y-6">
      {!futureEmbeddingModel ? (
        <>
          {settings?.settings.needs_reindexing && (
            <div className="p-3 rounded-08 bg-yellow-500/10 border border-yellow-500/20 text-sm text-yellow-700 dark:text-yellow-300">
              Your search settings are out of date. We recommend updating and
              re-indexing.
            </div>
          )}

          {/* Embedding Model */}
          <CardSection>
            <Title className="mb-4">Embedding Model</Title>
            {currentEmbeddingModel ? (
              <div>
                <div className="text-base font-semibold text-text-05 mb-1">
                  {currentEmbeddingModel.model_name}
                </div>
                <p className="text-sm text-text-03 mb-4">
                  {currentEmbeddingModel.description ||
                    "The recommended default for most situations. If you aren't sure which model to use, this is probably the one."}
                </p>

                <div className="rounded-08 border border-border-01 overflow-hidden">
                  <DetailRow
                    label="Dimensions"
                    value={currentEmbeddingModel.model_dim.toLocaleString()}
                  />
                  <DetailRow
                    label="Provider"
                    value={getFormattedProviderName(
                      currentEmbeddingModel.provider_type
                    )}
                  />
                  <DetailRow
                    label="Normalized"
                    value={currentEmbeddingModel.normalize ? "Yes" : "No"}
                  />
                  {"embedding_precision" in currentEmbeddingModel &&
                    (currentEmbeddingModel as any).embedding_precision && (
                      <DetailRow
                        label="Precision"
                        value={
                          (currentEmbeddingModel as any).embedding_precision
                        }
                      />
                    )}
                  {currentEmbeddingModel.query_prefix && (
                    <DetailRow
                      label="Query Prefix"
                      value={
                        <code className="text-xs font-mono bg-background-neutral-02 px-1.5 py-0.5 rounded-04">
                          &quot;{currentEmbeddingModel.query_prefix}&quot;
                        </code>
                      }
                    />
                  )}
                  {currentEmbeddingModel.passage_prefix && (
                    <DetailRow
                      label="Passage Prefix"
                      value={
                        <code className="text-xs font-mono bg-background-neutral-02 px-1.5 py-0.5 rounded-04">
                          &quot;{currentEmbeddingModel.passage_prefix}&quot;
                        </code>
                      }
                    />
                  )}
                </div>
              </div>
            ) : (
              <p className="text-sm text-text-03">
                No embedding model configured yet.
              </p>
            )}
          </CardSection>

          {/* Post-processing */}
          <CardSection>
            <Title className="mb-4">Post-processing</Title>
            {searchSettings && (
              <div className="rounded-08 border border-border-01 overflow-hidden">
                <div className="flex items-center justify-between py-3 px-4 border-b border-border-01">
                  <div>
                    <div className="text-sm font-medium text-text-05">
                      Multipass Indexing
                    </div>
                    <div className="text-xs text-text-02 mt-0.5">
                      Re-rank results with multiple passes for better accuracy
                    </div>
                  </div>
                  <StatusBadge enabled={searchSettings.multipass_indexing} />
                </div>
                <div className="flex items-center justify-between py-3 px-4">
                  <div>
                    <div className="text-sm font-medium text-text-05">
                      Contextual RAG
                    </div>
                    <div className="text-xs text-text-02 mt-0.5">
                      Add document context to chunks for improved retrieval
                    </div>
                  </div>
                  <StatusBadge enabled={searchSettings.enable_contextual_rag} />
                </div>
              </div>
            )}
          </CardSection>

          {/* Query Expansion & Fusion (WS-E) */}
          <QueryExpansionSettings />

          {/* Action */}
          <div>
            <Button action href="/admin/embeddings" leftIcon={SvgSettings}>
              Update Search Settings
            </Button>
          </div>
        </>
      ) : (
        <UpgradingPage futureEmbeddingModel={futureEmbeddingModel} />
      )}
    </div>
  );
}

export default function Page() {
  return (
    <>
      <AdminPageTitle
        title="Search Settings"
        icon={SvgSearch}
        description="Manage embedding models, indexing strategies, and retrieval post-processing."
      />
      <Main />
    </>
  );
}
