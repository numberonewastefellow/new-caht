"use client";

import { useEffect, useState } from "react";
import CardSection from "@/components/admin/CardSection";
import Switch from "@/refresh-components/inputs/Switch";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/components/ui/text";
import { toast } from "@/hooks/useToast";
import { useStandardAnswerConfig } from "./hooks";
import { updateStandardAnswerConfig } from "./lib";

// Feature-config panel backed by the dedicated `standard_answer_config` table.
// The toggle gates whether the Slack bot posts standard answers at all; the two
// numeric knobs bound how many answers are posted per message and how much of a
// message is fed to the matcher (a ReDoS defence-in-depth control).
export default function ConfigPanel() {
  const { data, isLoading, refreshStandardAnswerConfig } =
    useStandardAnswerConfig();

  const [enabled, setEnabled] = useState(true);
  const [maxMatches, setMaxMatches] = useState(3);
  const [charLimit, setCharLimit] = useState(8000);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (data) {
      setEnabled(data.enabled);
      setMaxMatches(data.max_matches_per_message);
      setCharLimit(data.match_input_char_limit);
    }
  }, [data]);

  const dirty =
    !!data &&
    (data.enabled !== enabled ||
      data.max_matches_per_message !== maxMatches ||
      data.match_input_char_limit !== charLimit);

  async function handleSave() {
    setSaving(true);
    const response = await updateStandardAnswerConfig({
      enabled,
      max_matches_per_message: maxMatches,
      match_input_char_limit: charLimit,
    });
    setSaving(false);
    if (response.ok) {
      toast.success("Standard answers configuration saved");
      refreshStandardAnswerConfig();
    } else {
      const detail = await response.text();
      toast.error(`Failed to save configuration - ${detail}`);
    }
  }

  return (
    <CardSection className="mb-6">
      <div className="flex items-start justify-between gap-6">
        <div>
          <div className="flex items-center gap-2">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: "var(--virtualai-accent, var(--theme-primary-05))" }}
            />
            <Text className="font-semibold">Slack standard answers</Text>
          </div>
          <Text className="mt-1 text-subtle">
            When enabled, the Slack bot replies with a matching standard answer
            before generating a full LLM answer.
          </Text>
        </div>
        <div className="flex items-center gap-2 pt-1">
          <Text className="text-subtle">{enabled ? "On" : "Off"}</Text>
          <Switch
            checked={enabled}
            onCheckedChange={setEnabled}
            disabled={isLoading}
          />
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1">
          <Text className="text-subtle">Max answers per message</Text>
          <input
            type="number"
            min={1}
            max={25}
            value={maxMatches}
            disabled={isLoading}
            onChange={(e) => setMaxMatches(Number(e.target.value))}
            className="w-full rounded-lg border-2 border-border bg-transparent px-3 py-2 outline-none focus-within:border-accent"
          />
        </label>
        <label className="flex flex-col gap-1">
          <Text className="text-subtle">Match input character limit</Text>
          <input
            type="number"
            min={100}
            max={100000}
            value={charLimit}
            disabled={isLoading}
            onChange={(e) => setCharLimit(Number(e.target.value))}
            className="w-full rounded-lg border-2 border-border bg-transparent px-3 py-2 outline-none focus-within:border-accent"
          />
        </label>
      </div>

      <div className="mt-4 flex justify-end">
        <Button type="button" onClick={handleSave} disabled={!dirty || saving}>
          {saving ? "Saving..." : "Save changes"}
        </Button>
      </div>
    </CardSection>
  );
}
