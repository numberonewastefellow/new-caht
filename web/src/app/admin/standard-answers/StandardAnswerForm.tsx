"use client";

import { Form, Formik } from "formik";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import * as Yup from "yup";
import CardSection from "@/components/admin/CardSection";
import Button from "@/refresh-components/buttons/Button";
import {
  TextFormField,
  MarkdownFormField,
  BooleanFormField,
  SelectorFormField,
} from "@/components/Field";
import MultiSelectDropdown from "@/components/MultiSelectDropdown";
import { toast } from "@/hooks/useToast";
import { StandardAnswer, StandardAnswerCategory } from "@/lib/types";
import {
  createStandardAnswer,
  createStandardAnswerCategory,
  StandardAnswerCreationRequest,
  updateStandardAnswer,
} from "./lib";

const LIST_ROUTE = "/admin/standard-answers";

// The form models the "match any / match all" choice as a select; the wire format
// is the boolean `match_any_keywords`, so we translate at the edges.
const toMatchAny = (choice: "any" | "all") => choice === "any";
const toChoice = (matchAny: boolean): "any" | "all" => (matchAny ? "any" : "all");

export default function StandardAnswerForm({
  categories,
  existing,
}: {
  categories: StandardAnswerCategory[];
  existing?: StandardAnswer;
}) {
  const isUpdate = existing !== undefined;
  const router = useRouter();

  return (
    <CardSection>
      <Formik
        initialValues={{
          keyword: existing?.keyword ?? "",
          answer: existing?.answer ?? "",
          categories: existing?.categories ?? [],
          matchRegex: existing?.match_regex ?? false,
          keywordMode: existing ? toChoice(existing.match_any_keywords) : "all",
        }}
        validationSchema={Yup.object().shape({
          keyword: Yup.string()
            .required("A keyword or pattern is required")
            .min(1)
            .max(1000),
          answer: Yup.string().required("An answer is required").min(1),
          categories: Yup.array()
            .required()
            .min(1, "Attach at least one category"),
        })}
        onSubmit={async (values, helpers) => {
          helpers.setSubmitting(true);
          const payload: StandardAnswerCreationRequest = {
            keyword: values.keyword,
            answer: values.answer,
            matchRegex: values.matchRegex,
            matchAnyKeywords: toMatchAny(values.keywordMode as "any" | "all"),
            categories: values.categories.map((c) => c.id),
          };
          const response = isUpdate
            ? await updateStandardAnswer(existing.id, payload)
            : await createStandardAnswer(payload);
          helpers.setSubmitting(false);
          if (response.ok) {
            toast.success(
              isUpdate ? "Standard answer updated" : "Standard answer created"
            );
            router.push(`${LIST_ROUTE}?u=${Date.now()}` as Route);
          } else {
            const body = await response.json().catch(() => ({}));
            toast.error(
              `${isUpdate ? "Update" : "Create"} failed - ${
                body.detail || body.message || response.statusText
              }`
            );
          }
        }}
      >
        {({ isSubmitting, values, setFieldValue }) => (
          <Form>
            {values.matchRegex ? (
              <TextFormField
                name="keyword"
                label="Regex pattern"
                isCode
                tooltip="Fires when the message matches this regular expression. Patterns are validated for safety (no catastrophic backtracking)."
                placeholder="(?:it|support)\s*ticket"
              />
            ) : values.keywordMode === "any" ? (
              <TextFormField
                name="keyword"
                label="Keywords — match ANY (space or comma separated)"
                tooltip="Fires when the message contains at least one of these keywords."
                placeholder="ticket problem issue"
              />
            ) : (
              <TextFormField
                name="keyword"
                label="Keywords — match ALL (space or comma separated)"
                tooltip="Fires only when the message contains every one of these keywords."
                placeholder="it ticket"
              />
            )}

            <BooleanFormField
              name="matchRegex"
              label="Use a regex pattern"
              subtext="Match a regular expression instead of keywords."
              optional
            />

            {!values.matchRegex && (
              <SelectorFormField
                name="keywordMode"
                label="Keyword strategy"
                subtext="Require the message to contain any, or all, of the keywords."
                defaultValue="all"
                options={[
                  { name: "All keywords", value: "all" },
                  { name: "Any keyword", value: "any" },
                ]}
                onSelect={(selected) => setFieldValue("keywordMode", selected)}
              />
            )}

            <div className="w-full">
              <MarkdownFormField
                name="answer"
                label="Answer"
                placeholder="The canned answer, in Markdown."
              />
            </div>

            <div className="w-5/12">
              <MultiSelectDropdown
                name="categories"
                label="Categories"
                creatable
                options={categories.map((c) => ({
                  label: c.name,
                  value: c.id.toString(),
                }))}
                initialSelectedOptions={values.categories.map((c) => ({
                  label: c.name,
                  value: c.id.toString(),
                }))}
                onChange={(selected) =>
                  setFieldValue(
                    "categories",
                    selected.map((o) => ({
                      id: Number(o.value),
                      name: o.label,
                    }))
                  )
                }
                onCreate={async (name) => {
                  const response = await createStandardAnswerCategory({ name });
                  const created = await response.json();
                  return { label: created.name, value: created.id.toString() };
                }}
              />
            </div>

            <div className="flex py-4">
              <Button
                type="submit"
                disabled={isSubmitting}
                className="mx-auto w-64"
              >
                {isUpdate ? "Update standard answer" : "Create standard answer"}
              </Button>
            </div>
          </Form>
        )}
      </Formik>
    </CardSection>
  );
}
