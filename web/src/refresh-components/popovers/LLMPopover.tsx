"use client";

import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import Modal from "@/refresh-components/Modal";
import Tabs from "@/refresh-components/Tabs";
import ShadowDiv from "@/refresh-components/ShadowDiv";
import { LlmDescriptor, LlmManager } from "@/lib/hooks";
import { structureValue } from "@/lib/llm/utils";
import {
  getProviderIcon,
  AGGREGATOR_PROVIDERS,
} from "@/app/admin/configuration/llm/utils";
import { LLMProviderDescriptor } from "@/app/admin/configuration/llm/interfaces";
import { Slider } from "@/components/ui/slider";
import { useUser } from "@/providers/UserProvider";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import Text from "@/refresh-components/texts/Text";
import SimpleLoader from "@/refresh-components/loaders/SimpleLoader";
import { cn } from "@/lib/utils";
import { SvgCheck, SvgRefreshCw } from "@opal/icons";
import { OpenButton } from "@opal/components";
import Button from "@/refresh-components/buttons/Button";
import { LLMOption, LLMOptionGroup } from "./interfaces";
import {
  useCompareStore,
  MAX_COMPARE_MODELS,
  CompareModel,
} from "@/app/app/stores/useCompareStore";

// ============================================================================
// Types
// ============================================================================

export interface LLMPopoverProps {
  llmManager: LlmManager;
  requiresImageInput?: boolean;
  folded?: boolean;
  /** Custom icon when folded. Defaults to SvgRefreshCw. */
  foldedIcon?: React.FunctionComponent<{ className?: string; size?: number }>;
  /** Tooltip for the folded button. */
  foldedTooltip?: string;
  onSelect?: (value: string) => void;
  currentModelName?: string;
  disabled?: boolean;
}

// ============================================================================
// Helper Functions (exported for tests)
// ============================================================================

export function buildLlmOptions(
  llmProviders: LLMProviderDescriptor[] | undefined,
  currentModelName?: string
): LLMOption[] {
  if (!llmProviders) {
    return [];
  }

  // Track seen combinations of provider + exact model name to avoid true duplicates
  // (same model appearing from multiple LLM provider configs with same provider type)
  const seenKeys = new Set<string>();
  const options: LLMOption[] = [];

  llmProviders.forEach((llmProvider) => {
    llmProvider.model_configurations
      .filter(
        (modelConfiguration) =>
          modelConfiguration.is_visible ||
          modelConfiguration.name === currentModelName
      )
      .forEach((modelConfiguration) => {
        // Deduplicate by exact provider + model name combination
        const key = `${llmProvider.provider}:${modelConfiguration.name}`;
        if (seenKeys.has(key)) {
          return;
        }
        seenKeys.add(key);

        options.push({
          name: llmProvider.name,
          provider: llmProvider.provider,
          providerDisplayName:
            llmProvider.provider_display_name || llmProvider.provider,
          modelName: modelConfiguration.name,
          displayName:
            modelConfiguration.display_name || modelConfiguration.name,
          vendor: modelConfiguration.vendor || null,
          maxInputTokens: modelConfiguration.max_input_tokens,
          region: modelConfiguration.region || null,
          version: modelConfiguration.version || null,
          supportsReasoning: modelConfiguration.supports_reasoning || false,
          supportsImageInput: modelConfiguration.supports_image_input || false,
        });
      });
  });

  return options;
}

export function groupLlmOptions(
  filteredOptions: LLMOption[]
): LLMOptionGroup[] {
  const groups = new Map<string, Omit<LLMOptionGroup, "key">>();

  filteredOptions.forEach((option) => {
    const provider = option.provider.toLowerCase();
    const isAggregator = AGGREGATOR_PROVIDERS.has(provider);
    const groupKey =
      isAggregator && option.vendor
        ? `${provider}/${option.vendor.toLowerCase()}`
        : provider;

    if (!groups.has(groupKey)) {
      let displayName: string;

      if (isAggregator && option.vendor) {
        const vendorDisplayName =
          option.vendor.charAt(0).toUpperCase() + option.vendor.slice(1);
        displayName = `${option.providerDisplayName}/${vendorDisplayName}`;
      } else {
        displayName = option.providerDisplayName;
      }

      groups.set(groupKey, {
        displayName,
        options: [],
        Icon: getProviderIcon(provider),
      });
    }

    groups.get(groupKey)!.options.push(option);
  });

  const sortedKeys = Array.from(groups.keys()).sort((a, b) =>
    groups.get(a)!.displayName.localeCompare(groups.get(b)!.displayName)
  );

  return sortedKeys.map((key) => {
    const group = groups.get(key)!;
    return {
      key,
      displayName: group.displayName,
      options: group.options,
      Icon: group.Icon,
    };
  });
}

// ============================================================================
// ModelCard Sub-Component
// ============================================================================

interface ModelCardProps {
  option: LLMOption;
  isSelected: boolean;
  onSelect: () => void;
  disabled?: boolean;
}

const ModelCard = React.forwardRef<HTMLButtonElement, ModelCardProps>(
  ({ option, isSelected, onSelect, disabled = false }, ref) => {
    const ProviderIcon = getProviderIcon(option.provider, option.modelName);

    return (
      <button
        ref={ref}
        type="button"
        onClick={onSelect}
        disabled={disabled}
        className={cn(
          "relative flex flex-col items-start gap-1 p-3 rounded-12 border transition-colors text-left w-full",
          "virtualai-card-hover",
          isSelected
            ? "virtualai-model-card-selected"
            : "border-border-01 bg-background-neutral-00",
          disabled && "opacity-50 pointer-events-none"
        )}
      >
        {/* Row: provider icon + model name + selection circle */}
        <div className="flex items-center gap-2 w-full">
          <div className="size-6 rounded-06 virtualai-accent-icon-badge flex items-center justify-center shrink-0">
            <ProviderIcon size={14} />
          </div>
          <Text
            as="p"
            mainUiMuted
            className={cn(
              "truncate flex-1",
              isSelected ? "text-text-05 font-medium" : "text-text-04"
            )}
          >
            {option.displayName}
          </Text>
          <span
            className="flex items-center justify-center w-4 h-4 rounded-full shrink-0 border"
            style={{
              backgroundColor: isSelected
                ? "var(--virtualai-accent, var(--theme-primary-05))"
                : "transparent",
              borderColor: isSelected
                ? "transparent"
                : "var(--line-01)",
            }}
          >
            {isSelected && (
              <SvgCheck className="h-2.5 w-2.5 stroke-white shrink-0" />
            )}
          </span>
        </div>

        {/* Provider sublabel */}
        <Text as="p" secondaryBody text03 className="truncate w-full">
          {option.providerDisplayName || option.provider}
        </Text>

        {/* One-line description */}
        {option.description && (
          <Text as="p" secondaryBody text03 className="line-clamp-2 w-full">
            {option.description}
          </Text>
        )}

        {/* Capability pills */}
        {(option.supportsReasoning || option.supportsImageInput) && (
          <div className="flex items-center gap-1 flex-wrap mt-0.5">
            {option.supportsReasoning && (
              <span className="virtualai-capability-pill virtualai-capability-pill--reasoning">
                Reasoning
              </span>
            )}
            {option.supportsImageInput && (
              <span className="virtualai-capability-pill virtualai-capability-pill--vision">
                Vision
              </span>
            )}
          </div>
        )}
      </button>
    );
  }
);
ModelCard.displayName = "ModelCard";

// ============================================================================
// Main Component
// ============================================================================

export default function LLMPopover({
  llmManager,
  requiresImageInput,
  folded,
  foldedIcon,
  foldedTooltip,
  onSelect,
  currentModelName,
  disabled = false,
}: LLMPopoverProps) {
  const llmProviders = llmManager.llmProviders;
  const isLoadingProviders = llmManager.isLoadingProviders;

  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeProviderTab, setActiveProviderTab] = useState("all");
  const { user } = useUser();

  const [localTemperature, setLocalTemperature] = useState(
    llmManager.temperature ?? 0.5
  );

  useEffect(() => {
    setLocalTemperature(llmManager.temperature ?? 0.5);
  }, [llmManager.temperature]);

  const searchInputRef = useRef<HTMLInputElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const selectedCardRef = useRef<HTMLButtonElement>(null);

  const handleGlobalTemperatureChange = useCallback((value: number[]) => {
    const value_0 = value[0];
    if (value_0 !== undefined) {
      setLocalTemperature(value_0);
    }
  }, []);

  const handleGlobalTemperatureCommit = useCallback(
    (value: number[]) => {
      const value_0 = value[0];
      if (value_0 !== undefined) {
        llmManager.updateTemperature(value_0);
      }
    },
    [llmManager]
  );

  const llmOptions = useMemo(
    () => buildLlmOptions(llmProviders, currentModelName),
    [llmProviders, currentModelName]
  );

  // Filter options by vision capability (when images are uploaded) and search query
  const filteredOptions = useMemo(() => {
    let result = llmOptions;
    if (requiresImageInput) {
      result = result.filter((opt) => opt.supportsImageInput);
    }
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (opt) =>
          opt.displayName.toLowerCase().includes(query) ||
          opt.modelName.toLowerCase().includes(query) ||
          (opt.vendor && opt.vendor.toLowerCase().includes(query))
      );
    }
    return result;
  }, [llmOptions, searchQuery, requiresImageInput]);

  // Build tab list from grouped options (uses search-filtered, before tab filtering)
  const providerTabs = useMemo(() => {
    const groups = groupLlmOptions(filteredOptions);
    return [
      { key: "all", displayName: "All" },
      ...groups.map((g) => ({ key: g.key, displayName: g.displayName })),
    ];
  }, [filteredOptions]);

  // Filter by active provider tab
  const tabFilteredOptions = useMemo(() => {
    if (activeProviderTab === "all") return filteredOptions;
    return filteredOptions.filter((opt) => {
      const provider = opt.provider.toLowerCase();
      const isAggregator = AGGREGATOR_PROVIDERS.has(provider);
      const groupKey =
        isAggregator && opt.vendor
          ? `${provider}/${opt.vendor.toLowerCase()}`
          : provider;
      return groupKey === activeProviderTab;
    });
  }, [filteredOptions, activeProviderTab]);

  // Get display name for the model to show in the button
  const currentLlmDisplayName = useMemo(() => {
    const currentModel =
      currentModelName && currentModelName.trim()
        ? currentModelName
        : llmManager.currentLlm.modelName;
    if (!llmProviders) return currentModel;

    for (const provider of llmProviders) {
      const config = provider.model_configurations.find(
        (m) => m.name === currentModel
      );
      if (config) {
        return config.display_name || config.name;
      }
    }
    return currentModel;
  }, [llmProviders, currentModelName, llmManager.currentLlm.modelName]);

  // Reset state when modal closes
  useEffect(() => {
    if (!open) {
      setSearchQuery("");
      setActiveProviderTab("all");
    }
  }, [open]);

  // Auto-scroll to selected card when modal opens
  useEffect(() => {
    if (open && selectedCardRef.current) {
      const timer = setTimeout(() => {
        selectedCardRef.current?.scrollIntoView({
          behavior: "instant",
          block: "center",
        });
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [open]);

  const isSearching = searchQuery.trim().length > 0;

  // ── Multi-model compare selection ───────────────────────────────────────
  const compareModels = useCompareStore((s) => s.compareModels);
  const toggleCompareModel = useCompareStore((s) => s.toggleModel);
  const setCompareModels = useCompareStore((s) => s.setCompareModels);
  const resetCompare = useCompareStore((s) => s.reset);
  const compareActive = compareModels.length > 0;

  const optionToCompareModel = (option: LLMOption): CompareModel => ({
    name: option.name,
    provider: option.provider,
    modelName: option.modelName,
    displayName: option.displayName,
    providerDisplayName: option.providerDisplayName,
    supportsReasoning: option.supportsReasoning,
    supportsImageInput: option.supportsImageInput,
  });

  const isInCompare = (option: LLMOption) =>
    compareModels.some(
      (m) =>
        m.name === option.name &&
        m.provider === option.provider &&
        m.modelName === option.modelName
    );

  const handleToggleCompareMode = () => {
    if (compareActive) {
      resetCompare();
    } else {
      // Seed compare with the current primary model so it starts non-empty.
      setCompareModels([
        {
          name: llmManager.currentLlm.name,
          provider: llmManager.currentLlm.provider,
          modelName: llmManager.currentLlm.modelName,
        },
      ]);
    }
  };

  const handleSelectModel = (option: LLMOption) => {
    llmManager.updateCurrentLlm({
      modelName: option.modelName,
      provider: option.provider,
      name: option.name,
    } as LlmDescriptor);
    onSelect?.(structureValue(option.name, option.provider, option.modelName));
    setOpen(false);
  };

  return (
    <>
      {/* Trigger button */}
      <div data-testid="llm-popover-trigger">
        <OpenButton
          icon={
            folded
              ? (foldedIcon ?? SvgRefreshCw)
              : getProviderIcon(
                  llmManager.currentLlm.provider,
                  llmManager.currentLlm.modelName
                )
          }
          foldable={folded}
          disabled={disabled}
          tooltip={folded ? foldedTooltip : undefined}
          transient={open}
          onClick={() => !disabled && setOpen(true)}
        >
          {currentLlmDisplayName}
        </OpenButton>
      </div>

      {/* Model Selection Modal */}
      <Modal open={open} onOpenChange={setOpen}>
        <Modal.Content
          width="sm"
          height="lg"
          preventAccidentalClose={false}
          onOpenAutoFocus={(e) => {
            e.preventDefault();
            searchInputRef.current?.focus();
          }}
        >
          <Modal.Header title={compareActive ? "Compare models" : "Choose Model"}>
            {compareActive && (
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <span
                  className="text-xs font-semibold px-2 py-0.5 rounded-full"
                  style={{
                    backgroundColor:
                      "var(--virtualai-accent-subtle, color-mix(in srgb, var(--theme-primary-05) 12%, transparent))",
                    color: "var(--virtualai-accent, var(--theme-primary-05))",
                  }}
                >
                  {compareModels.length}/{MAX_COMPARE_MODELS} selected
                </span>
                <Text secondaryBody text03 className="text-xs">
                  Pick up to {MAX_COMPARE_MODELS} models to run side-by-side on
                  the same prompt.
                </Text>
              </div>
            )}
            <InputTypeIn
              ref={searchInputRef}
              leftSearchIcon
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={
                compareActive
                  ? "Search by model or provider..."
                  : "Search models..."
              }
              autoComplete="off"
            />
          </Modal.Header>

          <Modal.Body twoTone padding={0}>
            {/* Provider Tabs — only when multiple providers exist, and not in
                compare mode (compare shows one ungrouped grid). */}
            {providerTabs.length > 2 && !compareActive && (
              <div className="px-4 pt-3 bg-background-tint-00">
                <Tabs
                  value={activeProviderTab}
                  onValueChange={setActiveProviderTab}
                >
                  <Tabs.List variant="pill" enableScrollArrows>
                    {providerTabs.map((tab) => (
                      <Tabs.Trigger key={tab.key} value={tab.key}>
                        {tab.displayName}
                      </Tabs.Trigger>
                    ))}
                  </Tabs.List>
                </Tabs>
              </div>
            )}

            {/* Compare-models entry — single mode only. In compare mode the
                header shows the count and the footer handles clear/cancel, so
                this row is hidden (matches the mockup). */}
            {!compareActive && (
              <div className="flex items-center justify-end px-4 pt-2 bg-background-tint-00">
                <button
                  type="button"
                  onClick={handleToggleCompareMode}
                  className="text-xs font-medium"
                  style={{
                    color: "var(--virtualai-accent, var(--theme-primary-05))",
                  }}
                >
                  Compare models
                </button>
              </div>
            )}

            {/* Model Card Grid */}
            <ShadowDiv
              scrollContainerRef={scrollContainerRef}
              className="px-4 py-3 max-h-[24rem]"
            >
              {isLoadingProviders ? (
                <div className="flex items-center justify-center gap-2 py-8">
                  <SimpleLoader />
                  <Text secondaryBody text03>
                    Loading models...
                  </Text>
                </div>
              ) : tabFilteredOptions.length === 0 ? (
                <div className="flex flex-col items-center py-8 gap-1">
                  <Text as="p" text02 secondaryBody>
                    No models found
                  </Text>
                  {isSearching && (
                    <Text as="p" text01 secondaryBody>
                      Try a different search term
                    </Text>
                  )}
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-2">
                  {tabFilteredOptions.map((option) => {
                    const isSelected = compareActive
                      ? isInCompare(option)
                      : option.modelName ===
                          llmManager.currentLlm.modelName &&
                        option.provider === llmManager.currentLlm.provider;
                    return (
                      <ModelCard
                        key={`${option.name}-${option.modelName}`}
                        ref={isSelected ? selectedCardRef : undefined}
                        option={option}
                        isSelected={isSelected}
                        disabled={
                          compareActive &&
                          !isSelected &&
                          compareModels.length >= MAX_COMPARE_MODELS
                        }
                        onSelect={() =>
                          compareActive
                            ? toggleCompareModel(optionToCompareModel(option))
                            : handleSelectModel(option)
                        }
                      />
                    );
                  })}
                </div>
              )}
            </ShadowDiv>

            {/* Temperature Slider (shown if enabled in user prefs) */}
            {user?.preferences?.temperature_override_enabled && (
              <div className="px-4 py-3 border-t border-border-01">
                <div className="flex flex-col w-full gap-2">
                  <div className="flex flex-row items-center justify-between">
                    <Text as="p" secondaryBody text03>
                      Temperature
                    </Text>
                    <span
                      className="text-xs font-semibold tabular-nums px-1.5 py-0.5 rounded-full"
                      style={{
                        backgroundColor:
                          "color-mix(in srgb, var(--virtualai-accent, var(--theme-primary-05)) 10%, var(--background-neutral-01) 90%)",
                        color:
                          "var(--virtualai-accent, var(--theme-primary-05))",
                      }}
                    >
                      {localTemperature.toFixed(1)}
                    </span>
                  </div>
                  <Slider
                    value={[localTemperature]}
                    max={llmManager.maxTemperature}
                    min={0}
                    step={0.01}
                    onValueChange={handleGlobalTemperatureChange}
                    onValueCommit={handleGlobalTemperatureCommit}
                    className="w-full virtualai-slider"
                  />
                  <div className="flex items-center justify-between">
                    <Text as="span" secondaryBody text03 className="text-xs">
                      Precise
                    </Text>
                    <Text as="span" secondaryBody text03 className="text-xs">
                      Balanced
                    </Text>
                    <Text as="span" secondaryBody text03 className="text-xs">
                      Creative
                    </Text>
                  </div>
                </div>
              </div>
            )}

            {/* Compare footer */}
            {compareActive && (
              <div className="flex items-center justify-between gap-2 px-4 py-3 border-t border-border-01">
                <Button tertiary onClick={() => resetCompare()}>
                  Clear selection
                </Button>
                <div className="flex items-center gap-2">
                  <Button secondary onClick={() => setOpen(false)}>
                    Cancel
                  </Button>
                  <Button
                    onClick={() => setOpen(false)}
                    disabled={compareModels.length < 2}
                  >
                    Start compare
                  </Button>
                </div>
              </div>
            )}
          </Modal.Body>
        </Modal.Content>
      </Modal>
    </>
  );
}
