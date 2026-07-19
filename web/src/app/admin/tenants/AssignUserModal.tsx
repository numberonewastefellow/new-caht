"use client";

import * as Yup from "yup";
import { Form, Formik } from "formik";
import Modal from "@/refresh-components/Modal";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import { TextFormField, BooleanFormField } from "@/components/Field";
import { toast } from "@/hooks/useToast";
import { SvgUser } from "@opal/icons";
import { assignUserToTenant } from "./lib";

interface AssignUserModalProps {
  tenantId: string | null;
  onClose: () => void;
  onAssigned: () => void;
}

export default function AssignUserModal({
  tenantId,
  onClose,
  onAssigned,
}: AssignUserModalProps) {
  return (
    <Modal open={tenantId !== null} onOpenChange={() => onClose()}>
      <Modal.Content width="sm" height="sm">
        <Modal.Header
          icon={SvgUser}
          title="Assign User to Tenant"
          onClose={onClose}
          description={
            tenantId
              ? `Route a user's login to ${tenantId}.`
              : undefined
          }
        />
        <Modal.Body>
          <Formik
            initialValues={{ email: "", move_if_assigned: false }}
            validationSchema={Yup.object().shape({
              email: Yup.string()
                .email("Enter a valid email")
                .required("A user email is required"),
            })}
            onSubmit={async (values, helpers) => {
              if (!tenantId) return;
              helpers.setSubmitting(true);
              try {
                const result = await assignUserToTenant(
                  tenantId,
                  values.email.trim(),
                  values.move_if_assigned
                );
                toast.success(result.detail || "User assigned");
                onAssigned();
                onClose();
              } catch (error) {
                toast.error(
                  `Failed to assign user: ${
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
                <TextFormField
                  name="email"
                  label="User email"
                  placeholder="user@example.com"
                />
                <BooleanFormField
                  name="move_if_assigned"
                  label="Move if already assigned"
                  subtext="If the user is active in another tenant, move them here instead of failing."
                />
                <Text as="p" text03>
                  A user belongs to one active tenant at a time. Moving
                  deactivates their mapping elsewhere.
                </Text>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Assigning…" : "Assign User"}
                </Button>
              </Form>
            )}
          </Formik>
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}
