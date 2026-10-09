import { apiPath } from "./endpoints.js";

const apiBase = (import.meta.env.VITE_API_BASE_URL || "").trim().replace(/\/+$/, "");
const tokenKey = "theravoice.accessToken";
const unauthorizedEvent = "theravoice:unauthorized";

let sessionToken = null;

function validateBaseUrl() {
  if (!apiBase) return;
  let parsed;
  try {
    parsed = new URL(apiBase);
  } catch {
    throw new Error("VITE_API_BASE_URL must be an absolute HTTP(S) origin or blank for same-origin.");
  }
  if (!["http:", "https:"].includes(parsed.protocol) || parsed.pathname !== "/" || parsed.search || parsed.hash) {
    throw new Error("VITE_API_BASE_URL must be an HTTP(S) origin without a path, query, or fragment.");
  }
  if (typeof window !== "undefined" && window.location.protocol === "https:" && parsed.protocol !== "https:") {
    throw new Error("An HTTPS dashboard cannot call an HTTP API. Configure an HTTPS API origin.");
  }
}

export function getApiConfigurationError() {
  try {
    validateBaseUrl();
    return null;
  } catch (error) {
    return error.message;
  }
}

export function setSessionToken(token) {
  sessionToken = token || null;
  if (typeof window === "undefined") return;
  if (sessionToken) window.sessionStorage.setItem(tokenKey, sessionToken);
  else window.sessionStorage.removeItem(tokenKey);
}

export function getSessionToken() {
  if (sessionToken) return sessionToken;
  if (typeof window === "undefined") return null;
  sessionToken = window.sessionStorage.getItem(tokenKey);
  return sessionToken;
}

export function clearSessionToken() {
  setSessionToken(null);
}

export class ApiError extends Error {
  constructor(message, statusCode = 0, detail = null) {
    super(message);
    this.name = "ApiError";
    this.status = statusCode;
    this.detail = detail;
  }
}

function extractErrorMessage(payload, statusCode) {
  const detail = payload?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((issue) => issue?.msg).filter(Boolean);
    if (messages.length) return messages.join("; ");
  }
  if (typeof payload?.message === "string") return payload.message;
  return `The server returned an error (${statusCode}).`;
}

export async function request(endpoint, options = {}) {
  validateBaseUrl();
  const { signal, headers: suppliedHeaders, ...fetchOptions } = options;
  const headers = new Headers(suppliedHeaders || {});
  const token = getSessionToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const multipartBody = typeof FormData !== "undefined" && fetchOptions.body instanceof FormData;
  if (fetchOptions.body && !multipartBody && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort("Request timed out"), 30_000);
  const abortFromCaller = () => controller.abort(signal?.reason);
  signal?.addEventListener("abort", abortFromCaller, { once: true });

  let response;
  try {
    response = await fetch(`${apiBase}${apiPath(endpoint)}`, {
      ...fetchOptions,
      headers,
      signal: controller.signal,
    });
  } catch (error) {
    if (error.name === "AbortError") {
      throw new ApiError("The request was cancelled or timed out.");
    }
    throw new ApiError("Unable to reach the TheraVoice API. Check the API URL and network connection.");
  } finally {
    window.clearTimeout(timeoutId);
    signal?.removeEventListener("abort", abortFromCaller);
  }

  if (response.status === 401) {
    clearSessionToken();
    window.dispatchEvent(new CustomEvent(unauthorizedEvent));
  }
  if (!response.ok) {
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    throw new ApiError(extractErrorMessage(payload, response.status), response.status, payload?.detail ?? null);
  }
  if (response.status === 204) return null;

  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    throw new ApiError("The API returned a response in an unexpected format.", response.status);
  }
  try {
    return await response.json();
  } catch {
    throw new ApiError("The API returned malformed JSON.", response.status);
  }
}

export const api = Object.freeze({
  get: (endpoint, options = {}) => request(endpoint, { ...options, method: "GET" }),
  post: (endpoint, body, options = {}) =>
    request(endpoint, {
      ...options,
      method: "POST",
      ...(body === undefined ? {} : typeof FormData !== "undefined" && body instanceof FormData ? { body } : { body: JSON.stringify(body) }),
    }),
  patch: (endpoint, body, options = {}) =>
    request(endpoint, { ...options, method: "PATCH", body: JSON.stringify(body) }),
});

export { unauthorizedEvent };
