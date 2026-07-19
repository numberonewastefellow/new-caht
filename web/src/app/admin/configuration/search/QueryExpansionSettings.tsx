"use client";

import React, { useEffect, useState } from "react";
import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import CardSection from "@/components/admin/CardSection";
import Title from "@/components/ui/title";
import Button from "@/refresh-components/buttons/Button";
import Switch from "@/refresh-components/inputs/Switch";

// Mirrors backend om.search.api.schemas.ExpansionSettingsResponse
interface ExpansionSettings {
  enable_expansion: boolean;
  enable_keyword_expansion: boolean;
  enable_semantic_rephrase: boolean;
  enable_keyword_history_expansion: boolean;
  max_variants: number;
  num_results: number;
  num_retrieved_per_query: number;
  rrf_k: number;
  original_query_weight: number;
  semantic_variant_weight: number;
  keyword_variant_weight: number;
  enable_llm_section_selection: boolean;
}

const TOGGLES: {
  key: keyof ExpansionSettings;
  label: string;
  description: string;
}[] = [
  {
    key: "enable_expansion",
    label: "Query Expansion",
    description:
      "Master switch. Expand each query with LLM-generated variants before retrieval.",
  },
  {
    key: "enable_keyword_expansion",
    label: "Keyword Expansion",
    description: "Generate keyword-only (BM25) reformulations of the query.",
  },
  {
    key: "enable_semantic_rephrase",
    label: "History-aware Rephrase",
    description:
      "Rewrite the latest query into a standalone question using conversation context.",
  },
  {
    key: "enable_keyword_history_expansion",
    label: "History-aware Keyword Expansion",
    description: "Keyword reformulations that fold in conversation context.",
  },
  {
    key: "enable_llm_section_selection",
    label: "LLM Relevance Selection",
    description: "Ask the LLM which retrieved documents are actually relevant.",
  },
];

const NUMBERS: {
  key: keyof ExpansionSettings;
  label: string;
  description: string;
  step?: number;
  min?: number;
}[] = [
  {
    key: "max_variants",
    label: "Max variants per strategy",
    description: "Upper bound on keyword variants each strategy produces.",
    min: 1,
  },
  {
    key: "num_results",
    label: "Results returned",
    description: "Number of fused documents returned to the caller.",
    min: 1,
  },
  {
    key: "num_retrieved_per_query",
    label: "Retrieved per query",
    description: "Retrieval depth for each query variant before fusion.",
    min: 1,
  },
  {
    key: "rrf_k",
    label: "RRF k constant",
    description: "Rank-fusion smoothing constant (60 is a robust default).",
    min: 1,
  },
  {
    key: "original_query_weight",
    label: "Original query weight",
    description: "Fusion weight for the user's original query.",
    step: 0.1,
    min: 0,
  },
  {
    key: "semantic_variant_weight",
    label: "Semantic variant weight",
    description: "Fusion weight for the history-aware rephrase.",
    step: 0.1,
    min: 0,
  },
  {
    key: "keyword_variant_weight",
    label: "Keyword variant weight",
    description: "Fusion weight for keyword variants.",
    step: 0.1,
    min: 0,
  },
];

const EXPANSION_SETTINGS_URL = "/api/search/expansion-settings";

export default function QueryExpansionSettings() {
  const { data, error, isLoading, mutate } = useSWR<ExpansionSettings>(
    EXPANSION_SETTINGS_URL,
    errorHandlingFetcher
  );

  const [draft, setDraft] = useState<ExpansionSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<"idle" | "saved" | "error">("idle");

  useEffect(() => {
    if (data) setDraft(data);
  }, [data]);

  if (isLoading || !draft) {
    return null;
  }

  if (error) {
    return (
      <CardSection>
        <Title className="mb-2">Query Expansion &amp; Fusion</Title>
        <p className="text-sm text-text-03">
          Unable to load query-expansion settings.
        </p>
      </CardSection>
    );
  }

  const dirty =
    !!data && JSON.stringify(draft) !== JSON.stringify(data);

  function update<K extends keyof ExpansionSettings>(
    key: K,
    value: ExpansionSettings[K]
  ) {
    setStatus("idle");
    setDraft((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  async function save() {
    if (!draft) return;
    setSaving(true);
    setStatus("idle");
    try {
      const response = await fetch(EXPANSION_SETTINGS_URL, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      });
      if (!response.ok) throw new Error(response.statusText);
      const updated = (await response.json()) as ExpansionSettings;
      await mutate(updated, { revalidate: false });
      setDraft(updated);
      setStatus("saved");
    } catch {
      setStatus("error");
    } finally {
      setSaving(false);
    }
  }

  const expansionOn = draft.enable_expansion;

  return (
    <CardSection>
      <Title className="mb-1">Query Expansion &amp; Fusion</Title>
      <p className="text-sm text-text-03 mb-4">
        Configure LLM query expansion and weighted reciprocal-rank fusion for the
        search experience.
      </p>

      <div className="rounded-08 border border-border-01 overflow-hidden">
        {TOGGLES.map((toggle) => {
          // Sub-toggles are meaningless when the master switch is off.
          const isMaster = toggle.key === "enable_expansion";
          const disabled = !isMaster && !expansionOn;
          return (
            <div
              key={toggle.key}
              className="flex items-center justify-between gap-4 py-3 px-4 border-b border-border-01 last:border-b-0"
            >
              <div>
                <div className="text-sm font-medium text-text-05">
                  {toggle.label}
                </div>
                <div className="text-xs text-text-02 mt-0.5">
                  {toggle.description}
                </div>
              </div>
              <Switch
                checked={draft[toggle.key] as boolean}
                disabled={disabled}
                onCheckedChange={(checked) => update(toggle.key, checked)}
              />
            </div>
          );
        })}
      </div>

      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
        {NUMBERS.map((field) => (
          <div
            key={field.key}
            className="flex items-center justify-between gap-3 py-2.5 px-4 rounded-08 border border-border-01"
          >
            <div>
              <div className="text-sm font-medium text-text-05">
                {field.label}
              </div>
              <div className="text-xs text-text-02 mt-0.5">
                {field.description}
              </div>
            </div>
            <input
              type="number"
              step={field.step ?? 1}
              min={field.min ?? 0}
              value={draft[field.key] as number}
              onChange={(event) => {
                const parsed = field.step
                  ? parseFloat(event.target.value)
                  : parseInt(event.target.value, 10);
                if (!Number.isNaN(parsed)) update(field.key, parsed as never);
              }}
              className="w-20 text-sm text-right rounded-04 border border-border-01 bg-background-neutral-01 px-2 py-1 text-text-05 focus:outline-none focus:border-[var(--virtualai-accent,var(--theme-primary-05))]"
            />
          </div>
        ))}
      </div>

      <div className="mt-4 flex items-center gap-3">
        <Button action onClick={save} disabled={!dirty || saving}>
          {saving ? "Saving..." : "Save Expansion Settings"}
        </Button>
        {status === "saved" && (
          <span className="text-sm text-green-600 dark:text-green-400">
            Saved.
          </span>
        )}
        {status === "error" && (
          <span className="text-sm text-red-600 dark:text-red-400">
            Failed to save.
          </span>
        )}
      </div>
    </CardSection>
  );
}
