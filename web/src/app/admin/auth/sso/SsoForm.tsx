"use client";

import React, { useEffect, useState } from "react";
import useSWR from "swr";
import { Label, SubLabel } from "@/components/Field";
import Title from "@/components/ui/title";
import CardSection from "@/components/admin/CardSection";
import Button from "@/refresh-components/buttons/Button";
import { toast } from "@/hooks/useToast";
import { useUser } from "@/providers/UserProvider";
import { errorHandlingFetcher } from "@/lib/fetcher";
import Message from "@/refresh-components/messages/Message";
import { FieldMessage } from "@/refresh-components/messages/FieldMessage";

const CONFIG_URL = "/api/admin/sso/saml/config";
const VERIFY_URL = "/api/admin/sso/saml/verify";

// Mirrors backend `SamlConfigView` (secrets never returned).
interface SamlConfigView {
  enabled: boolean;
  idp_entity_id: string;
  idp_sso_url: string;
  idp_slo_url: string | null;
  idp_x509_cert: string;
  sp_entity_id: string;
  sp_acs_url: string;
  sp_slo_url: string | null;
  sp_x509_cert: string | null;
  sp_private_key_set: boolean;
  want_assertions_signed: boolean;
  want_messages_signed: boolean;
  want_name_id_encrypted: boolean;
  authn_requests_signed: boolean;
  email_attribute_keys: string[] | null;
  first_name_attribute_key: string | null;
  last_name_attribute_key: string | null;
}

// Mirrors backend `SamlVerifyResult`.
type CheckStatus = "ok" | "warning" | "error";
interface SamlVerifyCheck {
  key: string;
  label: string;
  status: CheckStatus;
  detail: string;
}
interface SamlVerifyResult {
  valid: boolean;
  checks: SamlVerifyCheck[];
  sp_entity_id: string;
  sp_acs_url: string;
  sp_metadata_url: string;
  last_successful_login: { email: string; at: string } | null;
}

// ── Design-system field helpers (accent-aware, theme-safe) ─────────────────
function Checkbox({
  label,
  sublabel,
  checked,
  onChange,
}: {
  label: string;
  sublabel?: string;
  checked: boolean;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <label className="flex text-xs cursor-pointer py-2">
      <input
        checked={checked}
        onChange={onChange}
        type="checkbox"
        className="mr-3 w-4 h-4 my-auto rounded accent-[var(--virtualai-accent,var(--theme-primary-05))]"
      />
      <div>
        <span className="block font-medium text-text-05 text-sm">{label}</span>
        {sublabel && <SubLabel>{sublabel}</SubLabel>}
      </div>
    </label>
  );
}

function TextField({
  label,
  sublabel,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  label: string;
  sublabel?: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <label className="flex flex-col text-sm mb-4">
      <Label>{label}</Label>
      {sublabel && <SubLabel>{sublabel}</SubLabel>}
      <input
        type={type}
        className="mt-1.5 p-2.5 border border-border-01 rounded-08 w-full bg-background-neutral-00 text-text-05 placeholder:text-text-02 focus:outline-none focus:ring-2 focus:ring-[var(--virtualai-accent,var(--theme-primary-05))] focus:ring-opacity-30 transition-shadow"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
      />
    </label>
  );
}

function TextAreaField({
  label,
  sublabel,
  value,
  onChange,
  placeholder,
  rows = 4,
}: {
  label: string;
  sublabel?: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  placeholder?: string;
  rows?: number;
}) {
  return (
    <label className="flex flex-col text-sm mb-4">
      <Label>{label}</Label>
      {sublabel && <SubLabel>{sublabel}</SubLabel>}
      <textarea
        className="mt-1.5 p-2.5 border border-border-01 rounded-08 w-full font-mono text-xs bg-background-neutral-00 text-text-05 placeholder:text-text-02 focus:outline-none focus:ring-2 focus:ring-[var(--virtualai-accent,var(--theme-primary-05))] focus:ring-opacity-30 transition-shadow"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        rows={rows}
      />
    </label>
  );
}

export function SsoForm() {
  const { isAdmin } = useUser();
  const { data, error, isLoading, mutate } = useSWR<SamlConfigView>(
    isAdmin ? CONFIG_URL : null,
    errorHandlingFetcher
  );

  const [form, setForm] = useState<SamlConfigView | null>(null);
  const [privateKeyInput, setPrivateKeyInput] = useState("");
  const [emailKeysText, setEmailKeysText] = useState("");
  const [saving, setSaving] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState<SamlVerifyResult | null>(null);

  useEffect(() => {
    if (data) {
      setForm(data);
      setEmailKeysText((data.email_attribute_keys ?? []).join("\n"));
      setPrivateKeyInput("");
    }
  }, [data]);

  if (!isAdmin) {
    return (
      <CardSection>
        <p className="text-sm text-text-04">
          You must be an admin to manage single sign-on settings.
        </p>
      </CardSection>
    );
  }

  if (isLoading || !form) {
    return (
      <CardSection>
        <p className="text-sm text-text-04">Loading SSO configuration…</p>
      </CardSection>
    );
  }

  if (error) {
    return (
      <CardSection>
        <p className="text-sm text-text-04">
          Failed to load SSO configuration.
        </p>
      </CardSection>
    );
  }

  const set = <K extends keyof SamlConfigView>(
    key: K,
    value: SamlConfigView[K]
  ) => setForm((prev) => (prev ? { ...prev, [key]: value } : prev));

  const handleSave = async () => {
    if (!form) return;
    setSaving(true);

    const emailKeys = emailKeysText
      .split(/[\n,]/)
      .map((k) => k.trim())
      .filter((k) => k.length > 0);

    const payload = {
      enabled: form.enabled,
      idp_entity_id: form.idp_entity_id,
      idp_sso_url: form.idp_sso_url,
      idp_slo_url: form.idp_slo_url,
      idp_x509_cert: form.idp_x509_cert,
      sp_entity_id: form.sp_entity_id,
      sp_acs_url: form.sp_acs_url,
      sp_slo_url: form.sp_slo_url,
      sp_x509_cert: form.sp_x509_cert,
      // null → leave the stored key unchanged (see backend upsert semantics).
      sp_private_key: privateKeyInput.trim() === "" ? null : privateKeyInput,
      want_assertions_signed: form.want_assertions_signed,
      want_messages_signed: form.want_messages_signed,
      want_name_id_encrypted: form.want_name_id_encrypted,
      authn_requests_signed: form.authn_requests_signed,
      email_attribute_keys: emailKeys.length > 0 ? emailKeys : null,
      first_name_attribute_key: form.first_name_attribute_key,
      last_name_attribute_key: form.last_name_attribute_key,
    };

    try {
      const response = await fetch(CONFIG_URL, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const detail = (await response.json())?.detail ?? "Unknown error";
        throw new Error(
          typeof detail === "string" ? detail : JSON.stringify(detail)
        );
      }
      await mutate();
      toast.success("SSO configuration saved.");
    } catch (e) {
      toast.error(
        `Failed to save SSO configuration: ${
          e instanceof Error ? e.message : String(e)
        }`
      );
    } finally {
      setSaving(false);
    }
  };

  const handleVerify = async () => {
    setVerifying(true);
    setVerifyResult(null);
    try {
      const response = await fetch(VERIFY_URL);
      if (!response.ok) {
        const detail = (await response.json())?.detail ?? "Unknown error";
        throw new Error(
          typeof detail === "string" ? detail : JSON.stringify(detail)
        );
      }
      setVerifyResult((await response.json()) as SamlVerifyResult);
    } catch (e) {
      toast.error(
        `Verification failed: ${e instanceof Error ? e.message : String(e)}`
      );
    } finally {
      setVerifying(false);
    }
  };

  const checkVariant = (status: CheckStatus) =>
    status === "ok" ? "success" : status === "warning" ? "warning" : "error";

  return (
    <div className="flex flex-col gap-6 max-w-3xl">
      {/* Enablement */}
      <CardSection>
        <Title>Status</Title>
        <SubLabel>
          Turn SAML SSO on once the identity-provider details below are complete
          and verified.
        </SubLabel>
        <div className="mt-2">
          <Checkbox
            label="Enable SAML single sign-on"
            sublabel="When enabled, users authenticate through your identity provider."
            checked={form.enabled}
            onChange={(e) => set("enabled", e.target.checked)}
          />
        </div>
      </CardSection>

      {/* Identity Provider */}
      <CardSection>
        <Title>Identity Provider (IdP)</Title>
        <SubLabel>
          These values come from your IdP&apos;s SAML metadata (Entra, Okta, …).
        </SubLabel>
        <div className="mt-4">
          <TextField
            label="IdP Entity ID"
            sublabel="The IdP&apos;s issuer / entity identifier."
            value={form.idp_entity_id}
            onChange={(e) => set("idp_entity_id", e.target.value)}
            placeholder="https://sts.windows.net/…/"
          />
          <TextField
            label="IdP Sign-On URL"
            sublabel="SingleSignOnService (HTTP-Redirect) URL."
            value={form.idp_sso_url}
            onChange={(e) => set("idp_sso_url", e.target.value)}
            placeholder="https://login.microsoftonline.com/…/saml2"
          />
          <TextField
            label="IdP Logout URL"
            sublabel="Optional SingleLogoutService URL."
            value={form.idp_slo_url ?? ""}
            onChange={(e) => set("idp_slo_url", e.target.value || null)}
            placeholder="https://login.microsoftonline.com/…/saml2"
          />
          <TextAreaField
            label="IdP X.509 Certificate"
            sublabel="The IdP signing certificate (PEM). Public metadata."
            value={form.idp_x509_cert}
            onChange={(e) => set("idp_x509_cert", e.target.value)}
            placeholder="-----BEGIN CERTIFICATE-----&#10;…&#10;-----END CERTIFICATE-----"
            rows={6}
          />
        </div>
      </CardSection>

      {/* Service Provider */}
      <CardSection>
        <Title>Service Provider (this app)</Title>
        <SubLabel>
          Register these values at your IdP. The ACS URL is where assertions are
          posted.
        </SubLabel>
        <div className="mt-4">
          <TextField
            label="SP Entity ID"
            sublabel="This application&apos;s SAML entity identifier."
            value={form.sp_entity_id}
            onChange={(e) => set("sp_entity_id", e.target.value)}
          />
          <TextField
            label="ACS URL (Assertion Consumer Service)"
            sublabel="Where the IdP posts the SAML response."
            value={form.sp_acs_url}
            onChange={(e) => set("sp_acs_url", e.target.value)}
          />
          <TextField
            label="SP Logout URL"
            sublabel="Optional. Where the IdP sends logout responses."
            value={form.sp_slo_url ?? ""}
            onChange={(e) => set("sp_slo_url", e.target.value || null)}
          />
          <TextAreaField
            label="SP X.509 Certificate"
            sublabel="Optional — only needed if the SP signs requests/logout."
            value={form.sp_x509_cert ?? ""}
            onChange={(e) => set("sp_x509_cert", e.target.value || null)}
            rows={5}
          />
          <TextAreaField
            label="SP Private Key"
            sublabel={
              form.sp_private_key_set
                ? "A private key is stored. Leave blank to keep it; paste a new key to replace it."
                : "Optional — only needed if the SP signs requests/logout. Stored encrypted."
            }
            value={privateKeyInput}
            onChange={(e) => setPrivateKeyInput(e.target.value)}
            placeholder={
              form.sp_private_key_set
                ? "•••••••••• (configured — leave blank to keep)"
                : "-----BEGIN PRIVATE KEY-----…"
            }
            rows={5}
          />
        </div>
      </CardSection>

      {/* Security */}
      <CardSection>
        <Title>Security</Title>
        <SubLabel>
          Strict validation is always on (signature, conditions, destination,
          audience, timestamps). These toggles tune signing requirements.
        </SubLabel>
        <div className="mt-2">
          <Checkbox
            label="Require signed assertions"
            sublabel="Reject responses whose assertions are not signed. Recommended."
            checked={form.want_assertions_signed}
            onChange={(e) => set("want_assertions_signed", e.target.checked)}
          />
          <Checkbox
            label="Require signed messages"
            sublabel="Require the whole SAML response to be signed."
            checked={form.want_messages_signed}
            onChange={(e) => set("want_messages_signed", e.target.checked)}
          />
          <Checkbox
            label="Encrypted NameID"
            sublabel="Expect the NameID to be encrypted."
            checked={form.want_name_id_encrypted}
            onChange={(e) => set("want_name_id_encrypted", e.target.checked)}
          />
          <Checkbox
            label="Sign AuthnRequests"
            sublabel="Sign outbound login/logout requests (requires an SP key above)."
            checked={form.authn_requests_signed}
            onChange={(e) => set("authn_requests_signed", e.target.checked)}
          />
        </div>
      </CardSection>

      {/* Attribute mapping */}
      <CardSection>
        <Title>Attribute Mapping</Title>
        <SubLabel>
          How to read the user&apos;s email (and optional name) from the
          assertion. Leave email keys blank to use the built-in defaults that
          cover Entra, Okta, ADFS, and Shibboleth.
        </SubLabel>
        <div className="mt-4">
          <TextAreaField
            label="Email attribute keys"
            sublabel="One key per line, tried in order. Falls back to the NameID."
            value={emailKeysText}
            onChange={(e) => setEmailKeysText(e.target.value)}
            placeholder={
              "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress\nemail\nmail"
            }
            rows={4}
          />
          <TextField
            label="First name attribute key"
            sublabel="Optional."
            value={form.first_name_attribute_key ?? ""}
            onChange={(e) =>
              set("first_name_attribute_key", e.target.value || null)
            }
          />
          <TextField
            label="Last name attribute key"
            sublabel="Optional."
            value={form.last_name_attribute_key ?? ""}
            onChange={(e) =>
              set("last_name_attribute_key", e.target.value || null)
            }
          />
        </div>
      </CardSection>

      <div className="flex justify-end gap-2">
        <Button
          secondary
          onClick={handleVerify}
          disabled={verifying || saving}
        >
          {verifying ? "Verifying…" : "Verify configuration"}
        </Button>
        <Button onClick={handleSave} disabled={saving || verifying}>
          {saving ? "Saving…" : "Save configuration"}
        </Button>
      </div>

      {verifyResult && (
        <CardSection>
          <Title>Verification result</Title>
          <SubLabel>
            Structural check of the saved configuration — this does not contact
            the identity provider. Run an actual login to confirm the full
            round-trip.
          </SubLabel>

          <div className="mt-3">
            {verifyResult.valid ? (
              <Message
                static
                success
                close={false}
                text="Configuration looks valid."
                description="python3-saml accepts the settings. Try signing in to confirm the IdP round-trip."
              />
            ) : (
              <Message
                static
                error
                close={false}
                text="Configuration has issues."
                description="Resolve the errors below, Save, then verify again."
              />
            )}
          </div>

          <div className="mt-4 flex flex-col gap-1.5">
            {verifyResult.checks.map((check) => (
              <FieldMessage key={check.key} variant={checkVariant(check.status)}>
                <FieldMessage.Content>
                  <span className="font-medium">{check.label}:</span>{" "}
                  {check.detail}
                </FieldMessage.Content>
              </FieldMessage>
            ))}
          </div>

          <div className="mt-5">
            <Label>Register these at your identity provider</Label>
            <div className="mt-1.5 flex flex-col gap-1 text-sm">
              <div>
                <span className="text-text-03">SP Entity ID:</span>{" "}
                <span className="font-mono text-text-05">
                  {verifyResult.sp_entity_id}
                </span>
              </div>
              <div>
                <span className="text-text-03">ACS URL:</span>{" "}
                <span className="font-mono text-text-05">
                  {verifyResult.sp_acs_url}
                </span>
              </div>
              <div>
                <a
                  href={verifyResult.sp_metadata_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline text-[var(--virtualai-accent,var(--theme-primary-05))]"
                >
                  View SP metadata XML
                </a>
              </div>
            </div>
          </div>

          <div className="mt-4">
            <Label>Most recent SAML session</Label>
            <SubLabel>
              {verifyResult.last_successful_login
                ? `${verifyResult.last_successful_login.email} — ${new Date(
                    verifyResult.last_successful_login.at
                  ).toLocaleString()}`
                : "No SAML login has completed yet."}
            </SubLabel>
          </div>
        </CardSection>
      )}
    </div>
  );
}
