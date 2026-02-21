"use client";

import { OnSubmitProps } from "@/hooks/useChatController";
import { useCurrentAgent } from "@/hooks/useAgents";
import { cn } from "@/lib/utils";
import Text from "@/refresh-components/texts/Text";
import { SvgArrowUpRight } from "@opal/icons";

export interface SuggestionsProps {
  onSubmit: (props: OnSubmitProps) => void;
}

export default function Suggestions({ onSubmit }: SuggestionsProps) {
  const currentAgent = useCurrentAgent();

  if (
    !currentAgent ||
    !currentAgent.starter_messages ||
    currentAgent.starter_messages.length === 0
  )
    return null;

  const handleSuggestionClick = (suggestion: string) => {
    onSubmit({
      message: suggestion,
      currentMessageFiles: [],
      deepResearch: false,
    });
  };

  return (
    <div className="max-w-[var(--app-page-main-content-width)] w-full p-1">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {currentAgent.starter_messages.map(({ message, name }, index) => (
          <button
            key={index}
            onClick={() => handleSuggestionClick(message)}
            className={cn(
              "text-left px-4 py-3 rounded-12",
              "bg-background-neutral-01 hover:bg-background-neutral-02",
              "border border-border-01 hover:border-border-02",
              "transition-all duration-150 ease-in-out",
              "group cursor-pointer flex items-start gap-2"
            )}
          >
            <SvgArrowUpRight className="w-4 h-4 mt-0.5 flex-shrink-0 text-text-02 group-hover:text-text-04 transition-colors" />
            <div className="min-w-0 flex-1">
              <Text
                as="p"
                mainUiBody
                text04
                className="line-clamp-2 group-hover:text-text-05 transition-colors"
              >
                {message}
              </Text>
              {name && (
                <Text as="p" secondaryBody text03 className="mt-0.5">
                  {name}
                </Text>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
