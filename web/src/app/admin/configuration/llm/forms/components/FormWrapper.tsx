"use client";

import { useState, ReactNode } from "react";
import useSWR, { useSWRConfig, KeyedMutator } from "swr";
import { toast } from "@/hooks/useToast";
import {
  LLMProviderView,
  WellKnownLLMProviderDescriptor,
} from "../../interfaces";
import { errorHandlingFetcher } from "@/lib/fetcher";
import Modal from "@/refresh-components/Modal";
import Text from "@/refresh-components/texts/Text";
import Button from "@/refresh-components/buttons/Button";
import { SvgSettings } from "@opal/icons";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { LLM_PROVIDERS_ADMIN_URL } from "../../constants";
import { getProviderIcon } from "../../utils";
import { getProviderColor } from "../../providerColors";

export interface ProviderFormContext {
  onClose: () => void;
  mutate: KeyedMutator<any>;
  isTesting: boolean;
  setIsTesting: (testing: boolean) => void;
  testError: string;
  setTestError: (error: string) => void;
  wellKnownLLMProvider: WellKnownLLMProviderDescriptor | undefined;
}

interface ProviderFormEntrypointWrapperProps {
  children: (context: ProviderFormContext) => ReactNode;
  providerName: string;
  providerEndpoint?: string;
  existingLlmProvider?: LLMProviderView;
  /** When true, renders a simple button instead of a card-based UI */
  buttonMode?: boolean;
  /** Custom button text for buttonMode (defaults to "Add {providerName}") */
  buttonText?: string;
  /** When true, renders no card/button UI — only the modal. Parent controls visibility. */
  renderless?: boolean;
  /** Controlled modal open state (used with renderless) */
  isOpen?: boolean;
  /** Callback when the modal requests close */
  onOpenChange?: (open: boolean) => void;
}

export function ProviderFormEntrypointWrapper({
  children,
  providerName,
  providerEndpoint,
  existingLlmProvider,
  buttonMode,
  buttonText,
  renderless,
  isOpen,
  onOpenChange,
}: ProviderFormEntrypointWrapperProps) {
  const [formIsVisible, setFormIsVisible] = useState(false);

  // Shared hooks
  const { mutate } = useSWRConfig();

  // Shared state for testing
  const [isTesting, setIsTesting] = useState(false);
  const [testError, setTestError] = useState<string>("");

  // Fetch model configurations for this provider
  const { data: wellKnownLLMProvider } = useSWR<WellKnownLLMProviderDescriptor>(
    providerEndpoint
      ? `/api/admin/llm/built-in/options/${providerEndpoint}`
      : null,
    errorHandlingFetcher
  );

  const onClose = () => {
    if (renderless && onOpenChange) {
      onOpenChange(false);
    } else {
      setFormIsVisible(false);
    }
  };

  // Determine effective visibility
  const isFormVisible = renderless ? (isOpen ?? false) : formIsVisible;

  async function handleSetAsDefault(): Promise<void> {
    if (!existingLlmProvider) return;

    const response = await fetch(
      `${LLM_PROVIDERS_ADMIN_URL}/${existingLlmProvider.id}/default`,
      {
        method: "POST",
      }
    );
    if (!response.ok) {
      const errorMsg = (await response.json()).detail;
      toast.error(`Failed to set provider as default: ${errorMsg}`);
      return;
    }

    await mutate(LLM_PROVIDERS_ADMIN_URL);
    toast.success("Provider set as default successfully!");
  }

  const context: ProviderFormContext = {
    onClose,
    mutate,
    isTesting,
    setIsTesting,
    testError,
    setTestError,
    wellKnownLLMProvider,
  };

  // Resolve provider icon and colors for the modal header
  const providerIcon = providerEndpoint
    ? getProviderIcon(providerEndpoint)
    : SvgSettings;
  const providerColors = providerEndpoint
    ? getProviderColor(providerEndpoint)
    : null;

  const modalTitle = existingLlmProvider
    ? `${existingLlmProvider.name ?? providerName} Settings`
    : `Connect ${providerName}`;
  const modalDescription = providerColors?.tagline;

  // Renderless mode: no card/button UI, modal controlled by parent
  if (renderless) {
    return isFormVisible ? (
      <Modal open onOpenChange={onClose}>
        <Modal.Content>
          <Modal.Header
            icon={providerIcon}
            title={modalTitle}
            description={modalDescription}
            onClose={onClose}
          />
          <Modal.Body>{children(context)}</Modal.Body>
        </Modal.Content>
      </Modal>
    ) : null;
  }

  // Button mode: simple button that opens a modal
  if (buttonMode && !existingLlmProvider) {
    return (
      <>
        <Button action onClick={() => setFormIsVisible(true)}>
          {buttonText ?? `Add ${providerName}`}
        </Button>

        {isFormVisible && (
          <Modal open onOpenChange={onClose}>
            <Modal.Content>
              <Modal.Header
                icon={providerIcon}
                title={`Connect ${providerName}`}
                description={modalDescription}
                onClose={onClose}
              />
              <Modal.Body>{children(context)}</Modal.Body>
            </Modal.Content>
          </Modal>
        )}
      </>
    );
  }

  // Card mode: card-based UI with modal
  return (
    <div>
      <div className="border p-3 bg-background-neutral-01 rounded-16 w-96 flex shadow-md">
        {existingLlmProvider ? (
          <>
            <div className="my-auto">
              <Text
                as="p"
                headingH3
                text04
                className="text-ellipsis overflow-hidden max-w-32"
              >
                {existingLlmProvider.name}
              </Text>
              <Text as="p" secondaryBody text03 className="italic">
                ({providerName})
              </Text>
              {!existingLlmProvider.is_default_provider && (
                <Text
                  as="p"
                  className={cn("text-action-link-05", "cursor-pointer")}
                  onClick={handleSetAsDefault}
                >
                  Set as default
                </Text>
              )}
            </div>

            {existingLlmProvider && (
              <div className="my-auto ml-3">
                {existingLlmProvider.is_default_provider ? (
                  <Badge variant="agent">Default</Badge>
                ) : (
                  <Badge variant="success">Enabled</Badge>
                )}
              </div>
            )}

            <div className="ml-auto my-auto">
              <Button
                action={!existingLlmProvider}
                secondary={!!existingLlmProvider}
                onClick={() => setFormIsVisible(true)}
              >
                Edit
              </Button>
            </div>
          </>
        ) : (
          <>
            <div className="my-auto">
              <Text as="p" headingH3>
                {providerName}
              </Text>
            </div>
            <div className="ml-auto my-auto">
              <Button action onClick={() => setFormIsVisible(true)}>
                Set up
              </Button>
            </div>
          </>
        )}
      </div>

      {isFormVisible && (
        <Modal open onOpenChange={onClose}>
          <Modal.Content>
            <Modal.Header
              icon={providerIcon}
              title={modalTitle}
              description={modalDescription}
              onClose={onClose}
            />
            <Modal.Body>{children(context)}</Modal.Body>
          </Modal.Content>
        </Modal>
      )}
    </div>
  );
}
