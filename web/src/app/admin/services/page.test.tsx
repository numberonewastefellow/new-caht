import React from "react";
import { fireEvent, render, screen, within } from "@tests/setup/test-utils";
import "@testing-library/jest-dom";
import Page from "./page";
import { PULSE_HEALTH_URL } from "@/lib/schedules/webhookHelp";

jest.mock("next/navigation", () => ({
  usePathname: () => "/admin/services",
}));

describe("Platform Services page", () => {
  it("shows the webhook worker's configuration and health on its card", () => {
    render(<Page />);

    expect(screen.getByText("Pulse Webhook Worker")).toBeInTheDocument();
    expect(screen.getByText(/Service pulse_webhook_worker/)).toBeInTheDocument();
    expect(screen.getByText(/webhooks\.workers_alive should be 1 or more/)).toBeInTheDocument();
  });

  it("links to the health endpoint", () => {
    render(<Page />);

    // One for Pulse Worker and one for this card
    const links = screen.getAllByRole("link", { name: "Pulse health (JSON)" });
    expect(links).toHaveLength(2);
    for (const link of links) {
      expect(link).toHaveAttribute("href", PULSE_HEALTH_URL);
    }
  });

  it("opens help with how to configure it and read its health", () => {
    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: /How this works: Pulse Webhook Worker/ }));

    const dialog = screen.getByRole("dialog");
    for (const title of [
      "What it does",
      "Start and scale",
      "Settings",
      "Security settings",
      "Check its health",
      "Reading the health response",
      "If something's wrong",
      "Not supported yet",
    ]) {
      expect(within(dialog).getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(within(dialog).getByText("PULSE_WEBHOOK_RATE_PER_IP")).toBeInTheDocument();
    expect(within(dialog).getByText(`GET ${PULSE_HEALTH_URL}`)).toBeInTheDocument();
  });

  it("keeps other services as they were, with no help button", () => {
    render(<Page />);

    expect(screen.getAllByRole("button", { name: /How this works/ })).toHaveLength(1);
    expect(screen.getByText("API Server")).toBeInTheDocument();
    expect(screen.getByText("MinIO Object Storage")).toBeInTheDocument();
  });
});
