"use client";

import * as Yup from "yup";
import { Form, Formik } from "formik";
import Modal from "@/refresh-components/Modal";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import { TextFormField } from "@/components/Field";
import { toast } from "@/hooks/useToast";
import { SvgArrowExchange } from "@opal/icons";
import { createScimToken } from "./lib";
import { ScimTokenCreatedResponse } from "./types";

interface CreateScimTokenModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (created: ScimTokenCreatedResponse) => void;
}

export default function CreateScimTokenModal({
  isOpen,
  onClose,
  onCreated,
}: CreateScimTokenModalProps) {
  return (
    <Modal open={isOpen} onOpenChange={() => onClose()}>
      <Modal.Content width="sm" height="sm">
        <Modal.Header
          icon={SvgArrowExchange}
          title="Generate SCIM Token"
          onClose={onClose}
          description="Create a bearer token for your identity provider (Okta, Entra ID, …). The raw token is shown only once."
        />
        <Modal.Body>
          <Formik
            initialValues={{ name: "" }}
            validationSchema={Yup.object().shape({
              name: Yup.string()
                .required("A name is required")
                .max(255, "Name is too long"),
            })}
            onSubmit={async (values, helpers) => {
              helpers.setSubmitting(true);
              try {
                const created = await createScimToken(values.name.trim());
                onCreated(created);
              } catch (error) {
                toast.error(
                  `Failed to create SCIM token: ${
                    error instanceof Error ? error.message : String(error)
                  }`
                );
              } finally {
                helpers.setSubmitting(false);
              }
            }}
          >
            {({ isSubmitting }) => (
              <Form className="overflow-visible px-2">
                <Text as="p" text03 className="mb-4">
                  Give the token a recognizable name so you can identify which
                  identity provider it belongs to.
                </Text>
                <TextFormField
                  name="name"
                  label="Token Name"
                  placeholder="e.g. Okta production"
                />
                <Button type="submit" disabled={isSubmitting}>
                  Generate
                </Button>
              </Form>
            )}
          </Formik>
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}
