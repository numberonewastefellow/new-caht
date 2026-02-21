"use client";

import { useState, ComponentType } from "react";
import { errorHandlingFetcher } from "@/lib/fetcher";
import useSWR from "swr";
import { Callout } from "@/components/ui/callout";
import Text from "@/refresh-components/texts/Text";
import Title from "@/components/ui/title";
import { ThreeDotsLoader } from "@/components/Loading";
import { LLMProviderView, LLMProviderName, LLMProviderFormProps } from "./interfaces";
import { LLM_PROVIDERS_ADMIN_URL } from "./constants";
import { ProviderIcon } from "./ProviderIcon";
import { Badge } from "@/components/ui/badge";
import { OpenAIForm } from "./forms/OpenAIForm";
import { AnthropicForm } from "./forms/AnthropicForm";
import { OllamaForm } from "./forms/OllamaForm";
import { AzureForm } from "./forms/AzureForm";
import { BedrockForm } from "./forms/BedrockForm";
import { VertexAIForm } from "./forms/VertexAIForm";
import { OpenRouterForm } from "./forms/OpenRouterForm";
import { CustomForm } from "./forms/CustomForm";
import { getFormComponentForProvider } from "./forms/getForm";
import { SvgPlus } from "@opal/icons";
import { toast } from "@/hooks/useToast";

interface ProviderTile {
  key: string;
  displayName: string;
  providerName: LLMProviderName;
  FormComponent: ComponentType<LLMProviderFormProps>;
}

const PROVIDER_TILES: ProviderTile[] = [
  {
    key: "openai",
    displayName: "OpenAI",
    providerName: LLMProviderName.OPENAI,
    FormComponent: OpenAIForm,
  },
  {
    key: "anthropic",
    displayName: "Anthropic",
    providerName: LLMProviderName.ANTHROPIC,
    FormComponent: AnthropicForm,
  },
  {
    key: "ollama_chat",
    displayName: "Ollama",
    providerName: LLMProviderName.OLLAMA_CHAT,
    FormComponent: OllamaForm,
  },
  {
    key: "azure",
    displayName: "Microsoft Azure",
    providerName: LLMProviderName.AZURE,
    FormComponent: AzureForm,
  },
  {
    key: "bedrock",
    displayName: "AWS Bedrock",
    providerName: LLMProviderName.BEDROCK,
    FormComponent: BedrockForm,
  },
  {
    key: "vertex_ai",
    displayName: "Google Vertex AI",
    providerName: LLMProviderName.VERTEX_AI,
    FormComponent: VertexAIForm,
  },
  {
    key: "openrouter",
    displayName: "OpenRouter",
    providerName: LLMProviderName.OPENROUTER,
    FormComponent: OpenRouterForm,
  },
];

export function LLMConfiguration() {
  const {
    data: existingLlmProviders,
    mutate,
  } = useSWR<LLMProviderView[]>(LLM_PROVIDERS_ADMIN_URL, errorHandlingFetcher);

  const [activeModal, setActiveModal] = useState<string | null>(null);

  if (!existingLlmProviders) {
    return <ThreeDotsLoader />;
  }

  const isFirstProvider = existingLlmProviders.length === 0;

  // Determine which provider tiles are already configured
  const configuredProviderNames = new Set(
    existingLlmProviders.map((p) => p.provider)
  );

  const unconfiguredTiles = PROVIDER_TILES.filter(
    (tile) => !configuredProviderNames.has(tile.providerName)
  );

  // Sort existing providers: default first
  const sortedProviders = [...existingLlmProviders].sort((a, b) => {
    if (a.is_default_provider && !b.is_default_provider) return -1;
    if (!a.is_default_provider && b.is_default_provider) return 1;
    return 0;
  });

  async function handleSetAsDefault(provider: LLMProviderView) {
    const response = await fetch(
      `${LLM_PROVIDERS_ADMIN_URL}/${provider.id}/default`,
      { method: "POST" }
    );
    if (!response.ok) {
      const errorMsg = (await response.json()).detail;
      toast.error(`Failed to set provider as default: ${errorMsg}`);
      return;
    }
    await mutate();
    toast.success("Provider set as default successfully!");
  }

  return (
    <>
      {/* Section 1: Active Providers */}
      <Title className="mb-2">Active Providers</Title>

      {sortedProviders.length > 0 ? (
        <>
          <Text as="p" className="mb-4">
            If multiple LLM providers are enabled, the default provider will be
            used for all &quot;Default&quot; Assistants. For user-created
            Assistants, you can select the LLM provider/model that best fits the
            use case!
          </Text>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sortedProviders.map((provider) => (
              <div
                key={provider.id}
                className="border border-border rounded-lg p-4 bg-background-neutral-01 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <ProviderIcon
                      provider={provider.provider}
                      modelName={provider.default_model_name}
                      size={28}
                      className=""
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Text
                        as="p"
                        headingH3
                        className="truncate"
                      >
                        {provider.name}
                      </Text>
                      {provider.is_default_provider ? (
                        <Badge variant="agent">Default</Badge>
                      ) : (
                        <Badge variant="success">Enabled</Badge>
                      )}
                    </div>
                    <Text as="p" secondaryBody text03 className="mt-0.5">
                      {provider.model_configurations.filter((m) => m.is_visible).length}{" "}
                      model{provider.model_configurations.filter((m) => m.is_visible).length !== 1 ? "s" : ""}{" "}
                      available
                    </Text>
                  </div>
                </div>

                <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border">
                  {!provider.is_default_provider && (
                    <button
                      className="text-sm text-action-link-05 hover:underline cursor-pointer"
                      onClick={() => handleSetAsDefault(provider)}
                    >
                      Set as default
                    </button>
                  )}
                  <button
                    className="ml-auto text-sm px-3 py-1.5 rounded-md border border-border hover:bg-background-neutral-02 transition-colors cursor-pointer"
                    onClick={() => setActiveModal(`existing-${provider.id}`)}
                  >
                    Configure
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <Callout type="warning" title="No LLM providers configured yet">
          Please set one up below in order to start using VertualAI!
        </Callout>
      )}

      {/* Section 2: Add Provider */}
      <Title className="mb-2 mt-8">Add Provider</Title>
      <Text as="p" className="mb-4">
        Select a provider to configure, or add a custom LLM provider.
      </Text>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {unconfiguredTiles.map((tile) => (
          <button
            key={tile.key}
            className="flex items-center gap-3 p-3 rounded-lg border border-border bg-background hover:bg-background-neutral-01 hover:shadow-sm transition-all cursor-pointer text-left"
            onClick={() => setActiveModal(tile.key)}
          >
            <ProviderIcon
              provider={tile.providerName}
              size={22}
              className=""
            />
            <div className="flex-1 min-w-0">
              <Text as="p" mainUiAction className="truncate">
                {tile.displayName}
              </Text>
              <Text as="p" secondaryBody text03 className="text-xs">
                Set up &rarr;
              </Text>
            </div>
          </button>
        ))}

        {/* Custom provider tile — always visible */}
        <button
          className="flex items-center gap-3 p-3 rounded-lg border border-dashed border-border bg-background hover:bg-background-neutral-01 hover:shadow-sm transition-all cursor-pointer text-left"
          onClick={() => setActiveModal("custom")}
        >
          <SvgPlus className="w-5 h-5 text-text-03" />
          <div className="flex-1 min-w-0">
            <Text as="p" mainUiAction className="truncate">
              Custom LLM
            </Text>
            <Text as="p" secondaryBody text03 className="text-xs">
              Set up &rarr;
            </Text>
          </div>
        </button>
      </div>

      {/* Renderless modals for "Add" tiles */}
      {PROVIDER_TILES.map((tile) => (
        <tile.FormComponent
          key={tile.key}
          shouldMarkAsDefault={isFirstProvider}
          renderless
          isOpen={activeModal === tile.key}
          onOpenChange={(open) => {
            if (!open) setActiveModal(null);
          }}
        />
      ))}

      {/* Custom form modal */}
      <CustomForm
        shouldMarkAsDefault={isFirstProvider}
        renderless
        isOpen={activeModal === "custom"}
        onOpenChange={(open) => {
          if (!open) setActiveModal(null);
        }}
      />

      {/* Renderless modals for existing providers */}
      {sortedProviders.map((provider) => {
        const FormComponent = getFormComponentForProvider(provider);
        return (
          <FormComponent
            key={`existing-${provider.id}`}
            existingLlmProvider={provider}
            renderless
            isOpen={activeModal === `existing-${provider.id}`}
            onOpenChange={(open) => {
              if (!open) setActiveModal(null);
            }}
          />
        );
      })}
    </>
  );
}
