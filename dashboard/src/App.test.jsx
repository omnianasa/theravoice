import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import App from "./App.jsx";
import { clearSessionToken, setSessionToken } from "./api/client.js";

afterEach(() => {
  clearSessionToken();
  vi.unstubAllGlobals();
  window.location.hash = "";
});

it("supports SPA section navigation and clears the session on sign out", async () => {
  setSessionToken("test-token");
  vi.stubGlobal("fetch", vi.fn(async (input, options = {}) => {
    const url = String(input);
    if (url.endsWith("/auth/me")) {
      return new Response(JSON.stringify({ id: "user-1", email: "user@example.test", display_name: "Test User" }), {
        status: 200, headers: { "Content-Type": "application/json" },
      });
    }
    if (url.endsWith("/auth/logout")) return new Response(null, { status: 204 });
    if (url.endsWith("/health")) {
      return new Response(JSON.stringify({ status: "ok", service: "theravoice" }), { status: 200, headers: { "Content-Type": "application/json" } });
    }
    if (url.endsWith("/info")) {
      return new Response(JSON.stringify({ service: "theravoice", version: "0.1.0", api_version: "v1", disclaimer: "Not a diagnosis." }), { status: 200, headers: { "Content-Type": "application/json" } });
    }
    if (url.endsWith("/integrations")) {
      return new Response(JSON.stringify({ integrations: [{ name: "bee", mode: "mock", configured: true, enabled: true }] }), { status: 200, headers: { "Content-Type": "application/json" } });
    }
    return new Response(JSON.stringify({ detail: `Unhandled test request ${options.method || "GET"} ${url}` }), {
      status: 404, headers: { "Content-Type": "application/json" },
    });
  }));

  render(<App />);
  expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "Application workflow monitor" })).toBeInTheDocument();
  expect(screen.getByText("Session active")).toBeInTheDocument();
  expect(screen.getByText("Mock test mode")).toBeInTheDocument();
  expect(screen.getByText(/not live Bee data/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("link", { name: /Patients/ }));
  expect(await screen.findByRole("heading", { name: "Patients" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Patients/ })).toHaveAttribute("aria-current", "page");

  fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
  await waitFor(() => expect(screen.getByRole("heading", { name: "Welcome back" })).toBeInTheDocument());
  expect(sessionStorage.getItem("theravoice.accessToken")).toBeNull();
});
