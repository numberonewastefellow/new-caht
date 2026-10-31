import {
  curlExample,
  dedupNeedsPath,
  dedupOptions,
  defaultDedupSource,
  disabledReasonText,
  maskedToken,
  PulseWebhook,
  validateWebhookForm,
  webhookState,
} from "@/lib/schedules/webhooks";

function webhook(overrides: Partial<PulseWebhook>): PulseWebhook {
  return {
    enabled: true,
    revoked: false,
    disabled_reason: null,
    ...overrides,
  } as PulseWebhook;
}

describe("webhookState", () => {
  it("is active when enabled", () => {
    expect(webhookState(webhook({}))).toBe("active");
  });
  it("is paused when a person paused it", () => {
    expect(webhookState(webhook({ enabled: false }))).toBe("paused");
  });
  it("needs attention when the system paused it", () => {
    expect(
      webhookState(webhook({ enabled: false, disabled_reason: "access_revoked" }))
    ).toBe("attention");
  });
  it("revoked outranks everything, because resuming can't fix it", () => {
    expect(
      webhookState(webhook({ enabled: false, revoked: true, disabled_reason: "access_revoked" }))
    ).toBe("revoked");
    expect(webhookState(webhook({ enabled: true, revoked: true }))).toBe("revoked");
  });
});

describe("disabledReasonText", () => {
  it("explains known reasons and never shows a raw code", () => {
    expect(disabledReasonText(null)).toBeNull();
    expect(disabledReasonText("workflow_deleted")).toContain("deleted");
    expect(disabledReasonText("something_new")).toBe("Paused by the system");
  });
});

describe("dedup options", () => {
  it("offers webhook-id only for signed webhooks, which have that header", () => {
    expect(dedupOptions("standard_webhooks").map((o) => o.value)).toContain("webhook_id");
    expect(dedupOptions("header_token").map((o) => o.value)).not.toContain("webhook_id");
  });
  it("offers a header only when there's no signature for it to get around", () => {
    expect(dedupOptions("standard_webhooks").map((o) => o.value)).not.toContain("header");
    expect(dedupOptions("header_token").map((o) => o.value)).toContain("header");
  });
  it("defaults to what each mode can do", () => {
    expect(defaultDedupSource("standard_webhooks")).toBe("webhook_id");
    expect(defaultDedupSource("header_token")).toBe("none");
  });
  it("asks for a path only where one is used", () => {
    expect(dedupNeedsPath("header")).toBe(true);
    expect(dedupNeedsPath("json_path")).toBe(true);
    expect(dedupNeedsPath("webhook_id")).toBe(false);
    expect(dedupNeedsPath("none")).toBe(false);
  });
});

describe("validateWebhookForm", () => {
  const good = { name: "n", workflowId: 1, dedupSource: "none" as const, dedupPath: "" };
  it("accepts a complete form", () => {
    expect(validateWebhookForm(good)).toBeNull();
  });
  it("needs a workflow and a name", () => {
    expect(validateWebhookForm({ ...good, workflowId: null })).toMatch(/workflow/i);
    expect(validateWebhookForm({ ...good, name: "  " })).toMatch(/name/i);
  });
  it("needs a path for header and field sources", () => {
    expect(validateWebhookForm({ ...good, dedupSource: "header" })).toMatch(/header/i);
    expect(validateWebhookForm({ ...good, dedupSource: "json_path" })).toMatch(/field/i);
    expect(validateWebhookForm({ ...good, dedupSource: "json_path", dedupPath: "a.b" })).toBeNull();
  });
});

describe("curlExample", () => {
  const url = "https://x.example/api/hooks/whk_abc";
  it("signs for Standard Webhooks", () => {
    const text = curlExample({ url, authMode: "standard_webhooks", headerName: null, secret: "whsec_s" });
    expect(text).toContain("webhook-signature: v1,$SIG");
    expect(text).toContain("webhook-id: $ID");
    expect(text).toContain("SECRET='whsec_s'");
    expect(text).toContain(url);
  });
  it("sends the chosen header in secret-header mode", () => {
    const text = curlExample({ url, authMode: "header_token", headerName: "x-portal", secret: "s3" });
    expect(text).toContain("x-portal: s3");
    expect(text).not.toContain("webhook-signature");
  });
  it("uses a placeholder when the secret can't be read back", () => {
    expect(curlExample({ url, authMode: "header_token", headerName: null })).toContain(
      "x-webhook-secret: <your secret>"
    );
  });
  it("quotes values so they can't break out of the command", () => {
    const text = curlExample({ url: "https://x/'; rm -rf /", authMode: "header_token", headerName: null });
    expect(text).toContain(`'https://x/'\\''; rm -rf /'`);
  });
});

describe("maskedToken", () => {
  it("shows only the end", () => {
    expect(maskedToken("ab12")).toBe("whk_••••ab12");
  });
});
