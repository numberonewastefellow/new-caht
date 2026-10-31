import React from "react";
import { fireEvent, render, screen, waitFor, within } from "@tests/setup/test-utils";
import "@testing-library/jest-dom";
import AdminFeaturesPage from "./page";
import { WEBHOOKS_PAGE } from "@/lib/schedules/webhookHelp";

jest.mock("next/navigation", () => ({
  usePathname: () => "/admin/features",
}));

describe("New Features page", () => {
  it("shows the webhook card with its setup steps, linking to the Webhooks tab", () => {
    render(<AdminFeaturesPage />);

    const card = screen.getByRole("link", { name: /Webhook triggers/ });
    expect(card).toHaveAttribute("href", WEBHOOKS_PAGE);
    expect(within(card).getByText("How to set it up")).toBeInTheDocument();
    expect(within(card).getByText(/press New webhook/)).toBeInTheDocument();
  });

  it("opens help from a button that isn't inside the card's link", () => {
    render(<AdminFeaturesPage />);

    const button = screen.getByRole("button", { name: /How this works: Webhook triggers/ });
    expect(button.closest("a")).toBeNull();

    fireEvent.click(button);

    const dialog = screen.getByRole("dialog");
    for (const title of [
      "What it's for",
      "Webhook or schedule?",
      "Set it up",
      "Test it safely",
      "Send a real event",
      "What the caller gets back",
      "Stop it",
      "Before you rely on it",
    ]) {
      expect(within(dialog).getByRole("heading", { name: title })).toBeInTheDocument();
    }
  });

  it("returns keyboard focus to the (i) button when help closes", async () => {
    render(<AdminFeaturesPage />);

    const button = screen.getByRole("button", { name: /How this works: Webhook triggers/ });
    button.focus();
    fireEvent.click(button);
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await waitFor(() => expect(button).toHaveFocus());
  });

  it("only offers help on the cards that have it", () => {
    render(<AdminFeaturesPage />);

    expect(screen.getAllByRole("button", { name: /How this works/ })).toHaveLength(1);
    expect(screen.getByRole("link", { name: /Teams & Roles/ })).toBeInTheDocument();
    expect(screen.getAllByText("How to set it up")).toHaveLength(1);
  });
});
