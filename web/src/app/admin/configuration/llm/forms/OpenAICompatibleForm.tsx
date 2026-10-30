import { Form, Formik, FormikProps } from "formik";
import * as Yup from "yup";
import { useState } from "react";
import { TextFormField } from "@/components/Field";
import PasswordInputTypeInField from "@/refresh-components/form/PasswordInputTypeInField";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import Button from "@/refresh-components/buttons/Button";
import Separator from "@/refresh-components/Separator";
import Text from "@/refresh-components/texts/Text";
import { LLMProviderFormProps, ModelConfiguration } from "../interfaces";
import { LOCAL_SERVER_DOCKER_HINT } from "../constants";
import { fetchOpenAICompatibleModels } from "../utils";
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

export const OPENAI_COMPATIBLE_PROVIDER_NAME = "openai_compatible";
const OPENAI_COMPATIBLE_DISPLAY_NAME = "OpenAI-Compatible Server";
const API_BASE_PLACEHOLDER = "http://host.docker.internal:8000/v1";

interface OpenAICompatibleFormValues extends BaseLLMFormValues {
  api_key: string;
  api_base: string;
}

/** Add a model by id, for servers without a usable /v1/models listing. */
function ManualModelEntry({
  formikProps,
  currentModels,
  onAdd,
}: {
  formikProps: FormikProps<OpenAICompatibleFormValues>;
  currentModels: ModelConfiguration[];
  onAdd: (model: ModelConfiguration) => void;
}) {
  const [modelName, setModelName] = useState("");
  const trimmed = modelName.trim();
  const alreadyListed = currentModels.some((m) => m.name === trimmed);

  const addModel = () => {
    if (!trimmed || alreadyListed) return;
    onAdd({
      name: trimmed,
      display_name: trimmed,
      is_visible: true,
      max_input_tokens: null,
      supports_image_input: false,
    });
    const selected = formikProps.values.selected_model_names ?? [];
    formikProps.setFieldValue("selected_model_names", [...selected, trimmed]);
    if (!formikProps.values.default_model_name) {
      formikProps.setFieldValue("default_model_name", trimmed);
    }
    setModelName("");
  };

  return (
    <div className="flex flex-col gap-y-1">
      <Text as="p" mainUiAction>
        Add a model manually
      </Text>
      <Text as="p" secondaryBody text03>
        For servers that do not list models at /v1/models. Use the exact model
        id the server expects.
      </Text>
      <div className="flex flex-row items-center gap-2">
        <div className="flex-1">
          <InputTypeIn
            placeholder="e.g. Qwen/Qwen2.5-7B-Instruct"
            value={modelName}
            showClearButton={false}
            onChange={(e) => setModelName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addModel();
              }
            }}
          />
        </div>
        <Button
          type="button"
          secondary
          onClick={addModel}
          disabled={!trimmed || alreadyListed}
        >
          Add
        </Button>
      </div>
    </div>
  );
}

export function OpenAICompatibleForm({
  existingLlmProvider,
  shouldMarkAsDefault,
  renderless,
  isOpen,
  onOpenChange,
}: LLMProviderFormProps) {
  const [fetchedModels, setFetchedModels] = useState<ModelConfiguration[]>([]);

  return (
    <ProviderFormEntrypointWrapper
      providerName={OPENAI_COMPATIBLE_DISPLAY_NAME}
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
        const initialValues: OpenAICompatibleFormValues = {
          ...buildDefaultInitialValues(
            existingLlmProvider,
            modelConfigurations
          ),
          api_key: existingLlmProvider?.api_key ?? "",
          api_base: existingLlmProvider?.api_base ?? "",
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
              await submitLLMProvider({
                providerName: OPENAI_COMPATIBLE_PROVIDER_NAME,
                values,
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

              return (
                <Form className={LLM_FORM_CLASS_NAME}>
                  <DisplayNameField disabled={!!existingLlmProvider} />

                  <TextFormField
                    name="api_base"
                    label="API Base URL"
                    subtext={`Any server that speaks the OpenAI API (vLLM, llama.cpp server, LocalAI, ...). "/v1" is added if missing. ${LOCAL_SERVER_DOCKER_HINT}`}
                    placeholder={API_BASE_PLACEHOLDER}
                  />

                  <PasswordInputTypeInField
                    name="api_key"
                    label="API Key (Optional)"
                    subtext="Leave blank if your server does not require a key."
                  />

                  <FetchModelsButton
                    onFetch={() =>
                      fetchOpenAICompatibleModels({
                        api_base: formikProps.values.api_base,
                        api_key: formikProps.values.api_key,
                        api_key_changed:
                          formikProps.values.api_key !== initialValues.api_key,
                        provider_name: existingLlmProvider?.name,
                      })
                    }
                    isDisabled={!formikProps.values.api_base}
                    disabledHint="Enter the API base URL."
                    onModelsFetched={setFetchedModels}
                    autoFetchOnInitialLoad={!!existingLlmProvider}
                  />

                  <ManualModelEntry
                    formikProps={formikProps}
                    currentModels={currentModels}
                    onAdd={(model) =>
                      setFetchedModels([...currentModels, model])
                    }
                  />

                  <Separator />

                  <DisplayModels
                    modelConfigurations={currentModels}
                    formikProps={formikProps}
                    noModelConfigurationsMessage={
                      "Fetch the server's models, or add a model id manually, " +
                      "then choose which ones to make available in VertualAI."
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
