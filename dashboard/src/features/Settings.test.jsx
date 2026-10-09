import React from "react";
import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import Settings from "./Settings.jsx";

it("renders service-reported Bee configuration without calling it a live connection", async () => {
  vi.stubGlobal("fetch", vi.fn(async (input) => {
    const url = String(input);
    const body = url.endsWith("/integrations")
      ? { integrations: [{ name: "bee", mode: "proxy", enabled: true, configured: true }] }
      : url.endsWith("/info")
        ? { service: "theravoice", version: "0.1.0", api_version: "v1", disclaimer: "Not diagnostic." }
        : {
          patient_id: "patient-settings",
          mode: "proxy",
          source_configured: true,
          status: "never_synced",
          last_attempt_at: null,
          last_successful_sync_at: null,
          error_code: null,
        };
    return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
  }));
  render(
    <Settings
      user={{ id: "user-1", email: "user@example.test", display_name: "Test User" }}
      patient={{
        id: "patient-settings",
        display_name: "Patient",
        consent_llm_processing: false,
      }}
      onPatientUpdated={vi.fn()}
      onLogout={vi.fn()}
    />,
  );

  expect(await screen.findByText("proxy")).toBeInTheDocument();
  expect(screen.getByText("never_synced")).toBeInTheDocument();
  expect(screen.getByText(/does not confirm that Bee CLI/)).toBeInTheDocument();
});
