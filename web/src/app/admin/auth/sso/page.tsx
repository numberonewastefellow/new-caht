"use client";

import { AdminPageTitle } from "@/components/admin/Title";
import { SvgKey } from "@opal/icons";
import { SsoForm } from "./SsoForm";

export default function Page() {
  return (
    <>
      <AdminPageTitle
        title="Single Sign-On"
        icon={SvgKey}
        description="Connect a SAML identity provider (Microsoft Entra, Okta, ADFS, …). Users are just-in-time provisioned on first login; the first user becomes an admin."
      />

      <SsoForm />
    </>
  );
}
