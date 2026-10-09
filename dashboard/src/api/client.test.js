import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, clearSessionToken, setSessionToken, unauthorizedEvent } from "./client.js";
import { analysisService, authService, integrationService } from "./services.js";

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  clearSessionToken();
  vi.unstubAllGlobals();
});

describe("API client", () => {
  it("uses the verified versioned transcript route, bearer token, and request schema", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({
      patient_id: "patient-1",
      text_length: 12,
      biomarkers: { pause_rate: null },
      baseline_status: "insufficient_data",
      baseline: {},
      events: [],
      actions: [],
      context: {},
      status: "processed",
    }));
    vi.stubGlobal("fetch", fetchMock);
    setSessionToken("test-session-token");

    const result = await analysisService.transcript("patient-1", "A sample text.");

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/analyses/transcript");
    expect(options.method).toBe("POST");
    expect(options.headers.get("Authorization")).toBe("Bearer test-session-token");
    expect(JSON.parse(options.body)).toEqual({ patient_id: "patient-1", text: "A sample text." });
    expect(result.biomarkers.pause_rate).toBeNull();
  });

  it("constructs audio multipart form data without a manual content type", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ patient_id: "patient-2", status: "processed" }));
    vi.stubGlobal("fetch", fetchMock);
    const audioFile = new File(["audio"], "sample.wav", { type: "audio/wav" });

    await analysisService.audio("patient-2", audioFile, "Optional transcript");

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/analyses/audio");
    expect(options.method).toBe("POST");
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.body.get("patient_id")).toBe("patient-2");
    expect(options.body.get("file").name).toBe("sample.wav");
    expect(options.body.get("text")).toBe("Optional transcript");
    expect(options.headers.has("Content-Type")).toBe(false);
  });

  it("sends logout and Bee sync without fabricated JSON request bodies", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse({ patient_id: "p-1", status: "never_synced" }));
    vi.stubGlobal("fetch", fetchMock);

    await authService.logout();
    await integrationService.beeSync("p-1");

    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/auth/logout");
    expect(fetchMock.mock.calls[0][1].body).toBeUndefined();
    expect(fetchMock.mock.calls[1][0]).toBe("/api/v1/patients/p-1/integrations/bee/sync");
    expect(fetchMock.mock.calls[1][1].body).toBeUndefined();
  });

  it("surfaces validation details and clears the session on unauthorized responses", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ detail: [{ msg: "text is required" }] }, 422));
    vi.stubGlobal("fetch", fetchMock);
    await expect(api.get("/info")).rejects.toMatchObject({ status: 422, message: "text is required" });

    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: "Session is invalid or expired." }, 401));
    setSessionToken("expired-token");
    const onUnauthorized = vi.fn();
    window.addEventListener(unauthorizedEvent, onUnauthorized);
    await expect(api.get("/auth/me")).rejects.toBeInstanceOf(ApiError);
    expect(sessionStorage.getItem("theravoice.accessToken")).toBeNull();
    expect(onUnauthorized).toHaveBeenCalledOnce();
    window.removeEventListener(unauthorizedEvent, onUnauthorized);
  });

  it("rejects malformed successful response bodies and network failures", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(new Response("{", { status: 200, headers: { "Content-Type": "application/json" } }))
      .mockRejectedValueOnce(new TypeError("offline")));
    await expect(api.get("/info")).rejects.toThrow("malformed JSON");
    await expect(api.get("/info")).rejects.toThrow("Unable to reach the TheraVoice API");
  });
});
