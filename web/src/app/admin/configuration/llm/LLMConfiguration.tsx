"use client";

import { useState, ComponentType } from "react";
import { errorHandlingFetcher } from "@/lib/fetcher";
import useSWR from "swr";
import Text from "@/refresh-components/texts/Text";
import { ThreeDotsLoader } from "@/components/Loading";
import { LLMProviderView, LLMProviderName, LLMProviderFormProps } from "./interfaces";
import { LLM_PROVIDERS_ADMIN_URL } from "./constants";
import { ProviderIcon } from "./ProviderIcon";
import { OpenAIForm } from "./forms/OpenAIForm";
import { AnthropicForm } from "./forms/AnthropicForm";
import { OllamaForm } from "./forms/OllamaForm";
import { AzureForm } from "./forms/AzureForm";
import { BedrockForm } from "./forms/BedrockForm";
import { VertexAIForm } from "./forms/VertexAIForm";
import { OpenRouterForm } from "./forms/OpenRouterForm";
import { CustomForm } from "./forms/CustomForm";
import { getFormComponentForProvider } from "./forms/getForm";
import { SvgPlus, SvgSettings, SvgStar, SvgCpu } from "@opal/icons";
import { toast } from "@/hooks/useToast";
import { cn } from "@/lib/utils";
import { getProviderColor } from "./providerColors";

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
      <div className="mb-2 flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-theme-blue-05" />
        <Text as="p" headingH3 className="text-text-05">
          Active Providers
        </Text>
      </div>

      {sortedProviders.length > 0 ? (
        <>
          <Text as="p" secondaryBody text03 className="mb-4">
            The default provider powers all standard agents. Custom agents can use any enabled provider.
          </Text>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sortedProviders.map((provider) => {
              const colors = getProviderColor(provider.provider);
              const modelCount = provider.model_configurations.filter((m) => m.is_visible).length;
              return (
                <div
                  key={provider.id}
                  className={cn(
                    "relative overflow-hidden rounded-12 border bg-background-neutral-00 transition-all hover:shadow-md group cursor-pointer",
                    provider.is_default_provider
                      ? cn("border-l-[3px]", colors.border)
                      : "border-border-01 border-l-[3px]"
                  )}
                  onClick={() => setActiveModal(`existing-${provider.id}`)}
                >
                  {/* Card body */}
                  <div className="p-4">
                    <div className="flex items-start gap-3">
                      {/* Provider icon in tinted circle */}
                      <div className={cn(
                        "flex-shrink-0 w-10 h-10 rounded-12 flex items-center justify-center",
                        colors.bg
                      )}>
                        <ProviderIcon
                          provider={provider.provider}
                          modelName={provider.default_model_name}
                          size={22}
                          className=""
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <Text as="p" mainUiAction className="truncate font-semibold text-text-05">
                          {provider.name}
                        </Text>
                        <div className="flex items-center gap-2 mt-1">
                          {/* Status dot + label */}
                          {provider.is_default_provider ? (
                            <div className="flex items-center gap-1.5">
                              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: "var(--virtualai-accent, var(--theme-primary-05))" }} />
                              <Text as="span" secondaryBody className="text-xs font-medium" style={{ color: "var(--virtualai-accent, var(--theme-primary-05))" }}>
                                Primary
                              </Text>
                            </div>
                          ) : (
                            <div className="flex items-center gap-1.5">
                              <div className="w-2 h-2 rounded-full bg-status-success-05" />
                              <Text as="span" secondaryBody text03 className="text-xs">
                                Active
                              </Text>
                            </div>
                          )}
                          {/* Model count pill */}
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[0.625rem] font-medium bg-background-neutral-02 text-text-03">
                            {modelCount} model{modelCount !== 1 ? "s" : ""}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Card footer */}
                  <div className="flex items-center gap-2 px-4 py-2.5 border-t border-border-01 bg-background-neutral-01/50">
                    {!provider.is_default_provider && (
                      <button
                        className="flex items-center gap-1 text-xs font-medium text-text-03 hover:text-text-05 cursor-pointer transition-colors"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSetAsDefault(provider);
                        }}
                      >
                        <SvgStar className="w-3 h-3" />
                        Set as primary
                      </button>
                    )}
                    {provider.is_default_provider && (
                      <Text as="span" secondaryBody text03 className="text-xs">
                        Default for all agents
                      </Text>
                    )}
                    <button
                      className={cn(
                        "ml-auto flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-08",
                        "border transition-all",
                        colors.text, colors.border,
                        "hover:opacity-80"
                      )}
                      onClick={(e) => {
                        e.stopPropagation();
                        setActiveModal(`existing-${provider.id}`);
                      }}
                    >
                      <SvgSettings className="w-3 h-3" />
                      Configure
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      ) : (
        /* Empty state — illustrated */
        <div className="flex flex-col items-center justify-center py-12 px-6 rounded-12 border border-dashed border-border-01 bg-background-neutral-01/50">
          <div className="w-14 h-14 rounded-16 bg-theme-blue-01 flex items-center justify-center mb-4">
            <SvgCpu className="w-7 h-7 text-theme-blue-05" />
          </div>
          <Text as="p" mainUiAction className="text-text-05 font-semibold mb-1">
            No providers connected yet
          </Text>
          <Text as="p" secondaryBody text03 className="text-center max-w-sm">
            Connect your first LLM provider below to start using AI features across VertualAI.
          </Text>
        </div>
      )}

      {/* Section 2: Connect a Provider */}
      <div className="mb-2 mt-8 flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-theme-blue-05" />
        <Text as="p" headingH3 className="text-text-05">
          Connect a Provider
        </Text>
      </div>
      <Text as="p" secondaryBody text03 className="mb-4">
        Choose a model provider to get started, or connect a custom endpoint.
      </Text>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {unconfiguredTiles.map((tile) => {
          const colors = getProviderColor(tile.providerName);
          return (
            <button
              key={tile.key}
              className={cn(
                "relative flex flex-col items-center gap-3 p-4 rounded-12 border border-border-01 bg-background-neutral-00",
                "hover:shadow-md hover:scale-[1.02] transition-all cursor-pointer text-center overflow-hidden group"
              )}
              onClick={() => setActiveModal(tile.key)}
            >
              {/* Brand gradient bar at top */}
              <div className={cn("absolute top-0 left-0 right-0 h-1 bg-gradient-to-r", colors.gradient)} />

              {/* Provider icon in tinted circle */}
              <div className={cn(
                "w-12 h-12 rounded-16 flex items-center justify-center mt-1",
                colors.bg
              )}>
                <ProviderIcon
                  provider={tile.providerName}
                  size={24}
                  className=""
                />
              </div>

              <div className="flex flex-col items-center gap-0.5">
                <Text as="p" mainUiAction className="font-semibold text-text-05">
                  {tile.displayName}
                </Text>
                <Text as="p" secondaryBody text03 className="text-xs">
                  {colors.tagline}
                </Text>
              </div>

              {/* Connect button */}
              <span className={cn(
                "inline-flex items-center px-3 py-1 rounded-full text-xs font-medium text-white transition-opacity",
                "opacity-70 group-hover:opacity-100",
                colors.solid
              )}>
                Connect
              </span>
            </button>
          );
        })}

        {/* Custom provider tile */}
        <button
          className={cn(
            "relative flex flex-col items-center gap-3 p-4 rounded-12 border border-dashed border-border-01 bg-background-neutral-00",
            "hover:shadow-md hover:scale-[1.02] transition-all cursor-pointer text-center overflow-hidden group"
          )}
          onClick={() => setActiveModal("custom")}
        >
          {/* Accent gradient bar at top */}
          <div
            className="absolute top-0 left-0 right-0 h-1"
            style={{
              background: "linear-gradient(to right, var(--virtualai-accent, var(--theme-primary-05)), var(--virtualai-accent, var(--theme-primary-04)))"
            }}
          />

          {/* Plus icon in accent circle */}
          <div
            className="w-12 h-12 rounded-16 flex items-center justify-center mt-1 opacity-15"
            style={{ backgroundColor: "var(--virtualai-accent, var(--theme-primary-05))" }}
          />
          <div className="absolute top-[1.6rem]">
            <SvgPlus className="w-6 h-6" style={{ color: "var(--virtualai-accent, var(--theme-primary-05))" }} />
          </div>

          <div className="flex flex-col items-center gap-0.5">
            <Text as="p" mainUiAction className="font-semibold text-text-05">
              Custom LLM
            </Text>
            <Text as="p" secondaryBody text03 className="text-xs">
              OpenAI-compatible endpoint
            </Text>
          </div>

          <span
            className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium text-white transition-opacity opacity-70 group-hover:opacity-100"
            style={{ backgroundColor: "var(--virtualai-accent, var(--theme-primary-05))" }}
          >
            Connect
          </span>
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
