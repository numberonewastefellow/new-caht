"use client";

import * as Yup from "yup";
import { useEffect, useState } from "react";
import { Form, Formik } from "formik";
import Modal from "@/refresh-components/Modal";
import Button from "@/refresh-components/buttons/Button";
import { SelectorFormField, TextFormField } from "@/components/Field";
import { toast } from "@/hooks/useToast";
import { SvgShield } from "@opal/icons";
import { RateLimitPolicyArgs, RateLimitScope, SCOPE_LABELS } from "./types";
import { TEAMS_URL } from "./lib";

interface TeamOption {
  name: string;
  value: number;
}

interface CreatePolicyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (args: RateLimitPolicyArgs) => void;
}

export default function CreatePolicyModal({
  isOpen,
  onClose,
  onSubmit,
}: CreatePolicyModalProps) {
  const [teams, setTeams] = useState<TeamOption[]>([]);

  useEffect(() => {
    if (!isOpen) return;
    (async () => {
      try {
        const res = await fetch(TEAMS_URL);
        if (!res.ok) return;
        const data = await res.json();
        setTeams(
          (data ?? []).map((t: { name: string; id: number }) => ({
            name: t.name,
            value: t.id,
          }))
        );
      } catch (err) {
        toast.error(`Failed to load teams: ${err}`);
      }
    })();
  }, [isOpen]);

  return (
    <Modal open={isOpen} onOpenChange={onClose}>
      <Modal.Content width="sm" height="lg">
        <Modal.Header
          icon={SvgShield}
          title="Create a Rate Limit Policy"
          onClose={onClose}
        />
        <Modal.Body>
          <Formik
            initialValues={{
              scope: RateLimitScope.TENANT,
              period_hours: "",
              token_budget: "",
              team_id: undefined as number | undefined,
            }}
            validationSchema={Yup.object().shape({
              scope: Yup.string().required("Scope is required"),
              period_hours: Yup.number()
                .required("Time window is required")
                .min(1, "Time window must be at least 1 hour"),
              token_budget: Yup.number()
                .required("Token budget is required")
                .min(1, "Token budget must be at least 1"),
              team_id: Yup.number().when("scope", {
                is: RateLimitScope.TEAM,
                then: (schema) => schema.required("Team is required"),
                otherwise: (schema) => schema.notRequired(),
              }),
            })}
            onSubmit={(values, helpers) => {
              helpers.setSubmitting(true);
              const scope = values.scope as RateLimitScope;
              onSubmit({
                scope,
                enabled: true,
                period_hours: Number(values.period_hours),
                token_budget: Number(values.token_budget),
                team_id:
                  scope === RateLimitScope.TEAM
                    ? Number(values.team_id)
                    : null,
              });
              helpers.setSubmitting(false);
            }}
          >
            {({ isSubmitting, values }) => (
              <Form className="overflow-visible px-2 flex flex-col gap-3">
                <SelectorFormField
                  name="scope"
                  label="Scope"
                  includeDefault={false}
                  options={[
                    {
                      name: SCOPE_LABELS[RateLimitScope.TENANT],
                      value: RateLimitScope.TENANT,
                    },
                    {
                      name: SCOPE_LABELS[RateLimitScope.GLOBAL],
                      value: RateLimitScope.GLOBAL,
                    },
                    {
                      name: `${SCOPE_LABELS[RateLimitScope.USER]} (default)`,
                      value: RateLimitScope.USER,
                    },
                    {
                      name: SCOPE_LABELS[RateLimitScope.TEAM],
                      value: RateLimitScope.TEAM,
                    },
                  ]}
                />
                {values.scope === RateLimitScope.TEAM && (
                  <SelectorFormField
                    name="team_id"
                    label="Team"
                    includeDefault={false}
                    options={teams}
                  />
                )}
                <TextFormField
                  name="period_hours"
                  label="Time Window (hours)"
                  type="number"
                  placeholder="e.g. 24"
                />
                <TextFormField
                  name="token_budget"
                  label="Token Budget (tokens)"
                  type="number"
                  placeholder="e.g. 1000000"
                />
                <Button type="submit" disabled={isSubmitting}>
                  Create Policy
                </Button>
              </Form>
            )}
          </Formik>
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}
