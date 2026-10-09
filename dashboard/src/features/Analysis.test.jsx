import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import Analysis from "./Analysis.jsx";

afterEach(() => vi.unstubAllGlobals());

it("validates consent, submits a transcript and renders backend values including unavailable metrics", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
    patient_id: "patient-test",
    text_length: 18,
    biomarkers: { pause_rate: 0.25, speech_rate: null },
    baseline_status: "insufficient_data",
    baseline: {},
    events: [],
    actions: [],
    context: {},
    status: "processed",
  }), { status: 200, headers: { "Content-Type": "application/json" } }));
  vi.stubGlobal("fetch", fetchMock);
  const patient = {
    id: "patient-test",
    display_name: "Test patient",
    consent_data_storage: true,
    consent_audio_analysis: false,
  };
  const { rerender } = render(<Analysis patient={patient} />);

  fireEvent.change(screen.getByLabelText("Transcript"), { target: { value: "A sample transcript." } });
  fireEvent.click(screen.getByRole("button", { name: "Submit for analysis" }));

  expect(await screen.findByRole("heading", { name: "Analysis result" })).toBeInTheDocument();
  expect(screen.getByText("0.25")).toBeInTheDocument();
  expect(screen.getByText("Unavailable")).toBeInTheDocument();
  expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/analyses/transcript");

  const nextPatient = { ...patient, id: "patient-other", display_name: "Other patient" };
  rerender(<Analysis patient={nextPatient} />);
  expect(screen.queryByRole("heading", { name: "Analysis result" })).not.toBeInTheDocument();
});
