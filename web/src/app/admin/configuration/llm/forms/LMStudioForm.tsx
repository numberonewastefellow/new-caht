import { Form, Formik } from "formik";
import * as Yup from "yup";
import { useState } from "react";
import { TextFormField } from "@/components/Field";
import PasswordInputTypeInField from "@/refresh-components/form/PasswordInputTypeInField";
import Separator from "@/refresh-components/Separator";
import { LLMProviderFormProps, ModelConfiguration } from "../interfaces";
import { LOCAL_SERVER_DOCKER_HINT } from "../constants";
import { fetchLMStudioModels } from "../utils";
import {
  ProviderFormEntrypointWrapper,
  ProviderFormContext,
} from "./components/FormWrapper";
import { DisplayNameField } from "./components/DisplayNameField";
import { FormActionButtons } from "./components/FormActionButtons";
import { AdvancedOptions } from "./components/AdvancedOptions";
import { DisplayModels } from "./components/DisplayModels";
import { FetchModelsButton } from "./components/FetchModelsButton";
import {
  buildDefaultInitialValues,
  buildDefaultValidationSchema,
  buildAvailableModelConfigurations,
  submitLLMProvider,
  BaseLLMFormValues,
  LLM_FORM_CLASS_NAME,
} from "./formUtils";

export const LM_STUDIO_PROVIDER_NAME = "lm_studio";
const LM_STUDIO_DISPLAY_NAME = "LM Studio";
const DEFAULT_API_BASE = "http://host.docker.internal:1234";

interface LMStudioFormValues extends BaseLLMFormValues {
  api_base: string;
  custom_config: {
    LM_STUDIO_API_KEY?: string;
  };
}

export function LMStudioForm({
  existingLlmProvider,
  shouldMarkAsDefault,
  renderless,
  isOpen,
  onOpenChange,
}: LLMProviderFormProps) {
  const [fetchedModels, setFetchedModels] = useState<ModelConfiguration[]>([]);

  return (
    <ProviderFormEntrypointWrapper
      providerName={LM_STUDIO_DISPLAY_NAME}
      existingLlmProvider={existingLlmProvider}
      renderless={renderless}
      isOpen={isOpen}
      onOpenChange={onOpenChange}
    >
      {({
        onClose,
        mutate,
        isTesting,
        setIsTesting,
        testError,
        setTestError,
        wellKnownLLMProvider,
      }: ProviderFormContext) => {
        const modelConfigurations = buildAvailableModelConfigurations(
          existingLlmProvider,
          wellKnownLLMProvider
        );
        const initialApiKey =
          (existingLlmProvider?.custom_config?.LM_STUDIO_API_KEY as string) ??
          "";
        const initialValues: LMStudioFormValues = {
          ...buildDefaultInitialValues(
            existingLlmProvider,
            modelConfigurations
          ),
          api_base: existingLlmProvider?.api_base ?? DEFAULT_API_BASE,
          custom_config: {
            LM_STUDIO_API_KEY: initialApiKey,
          },
        };

        const validationSchema = buildDefaultValidationSchema().shape({
          api_base: Yup.string().required("API Base URL is required"),
        });

        return (
          <Formik
            initialValues={initialValues}
            validationSchema={validationSchema}
            validateOnMount={true}
            onSubmit={async (values, { setSubmitting }) => {
              // Drop an empty optional key so custom_config stays unset
              const filteredCustomConfig = Object.fromEntries(
                Object.entries(values.custom_config || {}).filter(
                  ([, v]) => v !== ""
                )
              );

              await submitLLMProvider({
                providerName: LM_STUDIO_PROVIDER_NAME,
                values: {
                  ...values,
                  custom_config:
                    Object.keys(filteredCustomConfig).length > 0
                      ? filteredCustomConfig
                      : undefined,
                },
                initialValues,
                modelConfigurations:
                  fetchedModels.length > 0
                    ? fetchedModels
                    : modelConfigurations,
                existingLlmProvider,
                shouldMarkAsDefault,
                setIsTesting,
                setTestError,
                mutate,
                onClose,
                setSubmitting,
              });
            }}
          >
            {(formikProps) => {
              const currentModels =
                fetchedModels.length > 0
                  ? fetchedModels
                  : existingLlmProvider?.model_configurations ||
                    modelConfigurations;
              const apiKey =
                formikProps.values.custom_config?.LM_STUDIO_API_KEY;

              return (
                <Form className={LLM_FORM_CLASS_NAME}>
                  <DisplayNameField disabled={!!existingLlmProvider} />

                  <TextFormField
                    name="api_base"
                    label="API Base URL"
                    subtext={`The LM Studio server URL (port 1234 by default). ${LOCAL_SERVER_DOCKER_HINT}`}
                    placeholder={DEFAULT_API_BASE}
                  />

                  <PasswordInputTypeInField
                    name="custom_config.LM_STUDIO_API_KEY"
                    label="API Key (Optional)"
                    subtext="Only needed when authentication is enabled in LM Studio's server settings."
                  />

                  <FetchModelsButton
                    onFetch={() =>
                      fetchLMStudioModels({
                        api_base: formikProps.values.api_base,
                        api_key: apiKey,
                        api_key_changed: apiKey !== initialApiKey,
                        provider_name: existingLlmProvider?.name,
                      })
                    }
                    isDisabled={!formikProps.values.api_base}
                    disabledHint="Enter the API base URL."
                    onModelsFetched={setFetchedModels}
                    autoFetchOnInitialLoad
                  />

                  <Separator />

                  <DisplayModels
                    modelConfigurations={currentModels}
                    formikProps={formikProps}
                    noModelConfigurationsMessage={
                      "No models found. Start the LM Studio server, load or " +
                      "download a model, then fetch again."
                    }
                    recommendedDefaultModel={null}
                    shouldShowAutoUpdateToggle={false}
                  />

                  <AdvancedOptions formikProps={formikProps} />

                  <FormActionButtons
                    isTesting={isTesting}
                    testError={testError}
                    existingLlmProvider={existingLlmProvider}
                    mutate={mutate}
                    onClose={onClose}
                    isFormValid={formikProps.isValid}
                  />
                </Form>
              );
            }}
          </Formik>
        );
      }}
    </ProviderFormEntrypointWrapper>
  );
}
