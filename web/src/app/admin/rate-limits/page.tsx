"use client";

import { useState } from "react";
import { mutate } from "swr";
import { AdminPageTitle } from "@/components/admin/Title";
import Text from "@/components/ui/text";
import { Section } from "@/layouts/general-layouts";
import CreateButton from "@/refresh-components/buttons/CreateButton";
import { toast } from "@/hooks/useToast";
import { SvgShield } from "@opal/icons";
import CreatePolicyModal from "./CreatePolicyModal";
import PolicyTable from "./PolicyTable";
import RemainingBudgetPanel from "./RemainingBudgetPanel";
import ThrottleHistoryChart from "./ThrottleHistoryChart";
import { BUDGET_URL, createPolicy, POLICIES_URL } from "./lib";
import { RateLimitPolicyArgs } from "./types";

function Main() {
  const [modalOpen, setModalOpen] = useState(false);

  const handleSubmit = async (args: RateLimitPolicyArgs) => {
    const res = await createPolicy(args);
    if (res.ok) {
      toast.success("Rate limit policy created");
      setModalOpen(false);
      mutate(POLICIES_URL);
      mutate(BUDGET_URL);
    } else {
      const body = await res.json().catch(() => ({}));
      const detail =
        typeof body?.detail === "string" ? body.detail : "Failed to create policy";
      toast.error(detail);
    }
  };

  return (
    <Section alignItems="stretch" justifyContent="start" height="auto">
      <Text>
        Rate limit policies cap how many tokens can be spent within a rolling time
        window. Enforcement uses a token-weighted sliding-window counter, so budgets are
        smooth (no burst at the window boundary), and any chat or search request that
        would exceed the cap is rejected with a{" "}
        <span className="font-medium">429</span> whose message tells the user the
        remaining budget and roughly when it resets. When several policies apply to one
        request, <span className="font-medium">all</span> of them must pass.
      </Text>

      <Text className="mt-3 font-medium text-text-darker">Scopes</Text>
      <ul className="list-disc ml-4 my-1">
        <li>
          <Text>
            <span className="font-medium">Tenant</span> /{" "}
            <span className="font-medium">Global</span> — one org-wide cap shared across
            every request in this workspace. (Tenant is the recommended label; Global is
            kept for parity and can be a second independent org-wide cap.)
          </Text>
        </li>
        <li>
          <Text>
            <span className="font-medium">Per-User</span> — a default budget applied to
            each user against their own usage (everyone gets the same allowance,
            counted individually).
          </Text>
        </li>
        <li>
          <Text>
            <span className="font-medium">Team</span> — a shared budget for everyone on a
            team.
          </Text>
        </li>
      </ul>

      <Text className="mt-3 font-medium text-text-darker">
        Setting up a policy
      </Text>
      <ol className="list-decimal ml-4 my-1">
        <li>
          <Text>
            Click <span className="font-medium">Create a Rate Limit Policy</span> and
            choose a scope (pick a Team if you chose Team scope).
          </Text>
        </li>
        <li>
          <Text>
            Set the <span className="font-medium">Time Window</span> in hours and the{" "}
            <span className="font-medium">Token Budget</span> in tokens (e.g. 24 hours /
            1,000,000 tokens). You can add several policies to the same scope with
            different windows (e.g. an hourly and a daily cap).
          </Text>
        </li>
        <li>
          <Text>
            In the table, use the checkbox to{" "}
            <span className="font-medium">enable / disable</span> a policy and the delete
            button to remove it.
          </Text>
        </li>
      </ol>

      <Text className="mt-2 text-text-muted">
        Note: changing a policy&apos;s budget or window in place isn&apos;t available in
        this screen yet — delete the policy and create a new one. Per-user overrides for a
        specific person and per-team / per-user history are available via the API only for
        now.
      </Text>

      <CreateButton onClick={() => setModalOpen(true)}>
        Create a Rate Limit Policy
      </CreateButton>

      <PolicyTable />

      <Text className="mt-4 text-text-muted">
        Below, the <span className="font-medium">Live Remaining Budget</span> gauge shows
        each policy&apos;s current usage — the bar turns amber past 75% and red once the
        budget is spent — and the <span className="font-medium">history</span> chart plots
        tokens used and requests throttled (429s) per hour.
      </Text>

      <div className="flex flex-col gap-6 mt-4">
        <RemainingBudgetPanel />
        <ThrottleHistoryChart />
      </div>

      <CreatePolicyModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleSubmit}
      />
    </Section>
  );
}

export default function Page() {
  return (
    <>
      <AdminPageTitle
        title="Rate Limits"
        icon={SvgShield}
        description="Cap how many tokens can be spent within a rolling time window, per scope. Requests over budget are rejected with a 429 until the window resets."
      />
      <Main />
    </>
  );
}
