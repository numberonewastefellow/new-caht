import { useState } from "react";
import { LoadingAnimation } from "@/components/Loading";
import Text from "@/refresh-components/texts/Text";
import Button from "@/refresh-components/buttons/Button";
import { SvgTrash, SvgChevronDown } from "@opal/icons";
import { LLMProviderView } from "../../interfaces";
import { LLM_PROVIDERS_ADMIN_URL } from "../../constants";
import { cn } from "@/lib/utils";

interface FormActionButtonsProps {
  isTesting: boolean;
  testError: string;
  existingLlmProvider?: LLMProviderView;
  mutate: (key: string) => void;
  onClose: () => void;
  isFormValid: boolean;
}

export function FormActionButtons({
  isTesting,
  testError,
  existingLlmProvider,
  mutate,
  onClose,
  isFormValid,
}: FormActionButtonsProps) {
  const [showDangerZone, setShowDangerZone] = useState(false);

  const handleDelete = async () => {
    if (!existingLlmProvider) return;

    const response = await fetch(
      `${LLM_PROVIDERS_ADMIN_URL}/${existingLlmProvider.id}`,
      {
        method: "DELETE",
      }
    );

    if (!response.ok) {
      const errorMsg = (await response.json()).detail;
      alert(`Failed to delete provider: ${errorMsg}`);
      return;
    }

    // If the deleted provider was the default, set the first remaining provider as default
    if (existingLlmProvider.is_default_provider) {
      const remainingProvidersResponse = await fetch(LLM_PROVIDERS_ADMIN_URL);
      if (remainingProvidersResponse.ok) {
        const remainingProviders = await remainingProvidersResponse.json();

        if (remainingProviders.length > 0) {
          const setDefaultResponse = await fetch(
            `${LLM_PROVIDERS_ADMIN_URL}/${remainingProviders[0].id}/default`,
            {
              method: "POST",
            }
          );
          if (!setDefaultResponse.ok) {
            console.error("Failed to set new default provider");
          }
        }
      }
    }

    mutate(LLM_PROVIDERS_ADMIN_URL);
    onClose();
  };

  return (
    <div className="flex flex-col gap-3 mt-4">
      {testError && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-08 bg-status-error-01 border border-status-error-03">
          <Text as="p" secondaryBody className="text-status-error-05">
            {testError}
          </Text>
        </div>
      )}

      {/* Primary actions */}
      <div className="flex w-full gap-2">
        <Button type="submit" disabled={isTesting || !isFormValid}>
          {isTesting ? (
            <Text as="p" inverted>
              <LoadingAnimation text="Testing" />
            </Text>
          ) : existingLlmProvider ? (
            "Save Changes"
          ) : (
            "Connect"
          )}
        </Button>
      </div>

      {/* Danger zone — collapsible, separate from primary actions */}
      {existingLlmProvider && (
        <div className="mt-2 border-t border-border-01 pt-3">
          <button
            type="button"
            onClick={() => setShowDangerZone(!showDangerZone)}
            className="flex items-center gap-1.5 text-xs text-text-03 hover:text-status-error-05 transition-colors cursor-pointer"
          >
            <SvgChevronDown className={cn("w-3 h-3 transition-transform", showDangerZone && "rotate-180")} />
            Danger Zone
          </button>

          {showDangerZone && (
            <div className="mt-2 p-3 rounded-08 border border-status-error-03 bg-status-error-01/50">
              <Text as="p" secondaryBody className="text-status-error-05 mb-2">
                Removing this provider will disconnect it from all agents using it.
              </Text>
              <Button danger leftIcon={SvgTrash} onClick={handleDelete}>
                Remove Provider
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
