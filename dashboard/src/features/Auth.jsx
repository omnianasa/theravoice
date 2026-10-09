import React, { useState } from "react";
import { authService } from "../api/services.js";
import { setSessionToken } from "../api/client.js";
import { ErrorNotice, Field } from "../components/Common.jsx";

export default function Auth({ onAuthenticated, configurationError, initialError }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ email: "", display_name: "", password: "" });
  const [error, setError] = useState(initialError || null);
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result = mode === "register"
        ? await authService.register(form)
        : await authService.login({ email: form.email, password: form.password });
      setSessionToken(result.access_token);
      onAuthenticated(result.user);
    } catch (requestError) {
      setError(requestError);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="brand brand-dark"><span className="brand-symbol">T</span><span>TheraVoice</span></div>
        <p className="eyebrow">Private monitoring workspace</p>
        <h1>{mode === "login" ? "Welcome back" : "Create your account"}</h1>
        <p className="muted">Sign in to access the patient records associated with your account.</p>
        {configurationError && <ErrorNotice error={{ message: configurationError }} />}
        {error && <ErrorNotice error={error} />}
        <form className="stack-form" onSubmit={submit}>
          {mode === "register" && (
            <Field
              label="Display name"
              name="display_name"
              autoComplete="name"
              minLength={1}
              maxLength={120}
              required
              value={form.display_name}
              onChange={(event) => setForm({ ...form, display_name: event.target.value })}
            />
          )}
          <Field
            label="Email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={form.email}
            onChange={(event) => setForm({ ...form, email: event.target.value })}
          />
          <Field
            label="Password"
            name="password"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            minLength={mode === "register" ? 12 : 1}
            required
            value={form.password}
            onChange={(event) => setForm({ ...form, password: event.target.value })}
            hint={mode === "register" ? "At least 12 characters." : undefined}
          />
          <button className="button button-primary button-wide" disabled={busy || Boolean(configurationError)} type="submit">
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>
        <button className="text-button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }} type="button">
          {mode === "login" ? "New to TheraVoice? Create an account" : "Already registered? Sign in"}
        </button>
        <p className="privacy-note">Sessions expire after 12 hours. Your access token stays in this browser tab session.</p>
      </section>
    </main>
  );
}
