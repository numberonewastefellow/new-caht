"use client";

import * as Yup from "yup";
import { Form, Formik } from "formik";
import Modal from "@/refresh-components/Modal";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import { TextFormField } from "@/components/Field";
import { toast } from "@/hooks/useToast";
import { SvgServer } from "@opal/icons";
import { createTenant } from "./lib";

interface CreateTenantModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export default function CreateTenantModal({
  isOpen,
  onClose,
  onCreated,
}: CreateTenantModalProps) {
  return (
    <Modal open={isOpen} onOpenChange={() => onClose()}>
      <Modal.Content width="sm" height="sm">
        <Modal.Header
          icon={SvgServer}
          title="Provision a Tenant"
          onClose={onClose}
          description="Creates an isolated Postgres schema, runs migrations, and routes the admin email to the new tenant. No billing is involved."
        />
        <Modal.Body>
          <Formik
            initialValues={{ admin_email: "" }}
            validationSchema={Yup.object().shape({
              admin_email: Yup.string()
                .email("Enter a valid email")
                .required("An admin email is required"),
            })}
            onSubmit={async (values, helpers) => {
              helpers.setSubmitting(true);
              try {
                const result = await createTenant(values.admin_email.trim());
                toast.success(`Tenant ${result.tenant_id} created`);
                onCreated();
                onClose();
              } catch (error) {
                toast.error(
                  `Failed to create tenant: ${
                    error instanceof Error ? error.message : String(error)
                  }`
                );
              } finally {
                helpers.setSubmitting(false);
              }
            }}
          >
            {({ isSubmitting }) => (
              <Form className="overflow-visible px-2 flex flex-col gap-4">
                <Text as="p" text03>
                  Provisioning can take a few seconds while the schema is
                  migrated.
                </Text>
                <TextFormField
                  name="admin_email"
                  label="Tenant admin email"
                  placeholder="admin@example.com"
                />
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Provisioning…" : "Create Tenant"}
                </Button>
              </Form>
            )}
          </Formik>
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}
