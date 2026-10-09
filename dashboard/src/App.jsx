import React, { useEffect, useMemo, useState } from "react";
import { clearSessionToken, getApiConfigurationError, getSessionToken } from "./api/client.js";
import { authService } from "./api/services.js";
import Auth from "./features/Auth.jsx";
import Overview from "./features/Overview.jsx";
import Patients from "./features/Patients.jsx";
import Analysis from "./features/Analysis.jsx";
import Trends from "./features/Trends.jsx";
import Care from "./features/Care.jsx";
import Settings from "./features/Settings.jsx";
import { StateMessage } from "./components/Common.jsx";

const sections = [
  { id: "overview", label: "Overview", icon: "◫" },
  { id: "patients", label: "Patients", icon: "◉" },
  { id: "analysis", label: "Speech analysis", icon: "⌁" },
  { id: "trends", label: "Trends & timeline", icon: "⌗" },
  { id: "care", label: "Reports & care", icon: "▤" },
  { id: "settings", label: "Settings & integrations", icon: "⚙" },
];

function readSection() {
  const candidate = window.location.hash.replace(/^#\/?/, "");
  if (!candidate) return "overview";
  return sections.some((section) => section.id === candidate) ? candidate || "overview" : "unknown";
}

export default function App() {
  const [section, setSection] = useState(readSection);
  const [user, setUser] = useState(null);
  const [patient, setPatient] = useState(null);
  const [authLoading, setAuthLoading] = useState(Boolean(getSessionToken()));
  const [mobileOpen, setMobileOpen] = useState(false);
  const [authError, setAuthError] = useState(null);
  const configurationError = useMemo(() => getApiConfigurationError(), []);

  useEffect(() => {
    const handleHash = () => setSection(readSection());
    window.addEventListener("hashchange", handleHash);
    return () => window.removeEventListener("hashchange", handleHash);
  }, []);

  useEffect(() => {
    const token = getSessionToken();
    if (!token) return undefined;
    let current = true;
    authService.me()
      .then((currentUser) => { if (current) setUser(currentUser); })
      .catch((error) => {
        if (!current) return;
        clearSessionToken();
        if (error.status !== 401) setAuthError(error);
      })
      .finally(() => { if (current) setAuthLoading(false); });
    return () => { current = false; };
  }, []);

  useEffect(() => {
    const unauthorized = () => {
      setUser(null);
      setPatient(null);
      setAuthError(new Error("Your session expired. Sign in again to continue."));
    };
    window.addEventListener("theravoice:unauthorized", unauthorized);
    return () => window.removeEventListener("theravoice:unauthorized", unauthorized);
  }, []);

  function navigate(nextSection) {
    if (!sections.some((item) => item.id === nextSection)) return;
    window.location.hash = `/${nextSection}`;
    setSection(nextSection);
    setMobileOpen(false);
  }

  async function logout() {
    try {
      await authService.logout();
    } catch {
      // Remove local access even if the service is unreachable.
    } finally {
      clearSessionToken();
      setUser(null);
      setPatient(null);
      setAuthError(null);
      navigate("overview");
    }
  }

  if (authLoading) return <main className="auth-page"><StateMessage kind="loading" title="Checking session" /></main>;
  if (!user) return <Auth onAuthenticated={(authenticatedUser) => { setAuthError(null); setUser(authenticatedUser); }} configurationError={configurationError} initialError={authError} />;
  if (configurationError) return <main className="auth-page"><StateMessage kind="error" title="API configuration error">{configurationError}</StateMessage></main>;

  const active = sections.find((item) => item.id === section);
  let page;
  switch (section) {
    case "overview": page = <Overview user={user} patient={patient} onNavigate={navigate} />; break;
    case "patients": page = <Patients patient={patient} onSelectPatient={setPatient} />; break;
    case "analysis": page = <Analysis patient={patient} />; break;
    case "trends": page = <Trends patient={patient} />; break;
    case "care": page = <Care patient={patient} />; break;
    case "settings": page = <Settings user={user} patient={patient} onPatientUpdated={setPatient} onLogout={logout} />; break;
    default: page = <StateMessage title="Section not found">That dashboard section is not available. Choose a destination from the sidebar.</StateMessage>;
  }

  return (
    <div className="app-shell">
      <button className={`mobile-scrim ${mobileOpen ? "visible" : ""}`} aria-label="Close navigation" onClick={() => setMobileOpen(false)} type="button" />
      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`} aria-label="Main navigation">
        <a href="#/overview" className="brand"><span className="brand-symbol">T</span><span>TheraVoice</span></a>
        <p className="sidebar-label">WORKSPACE</p>
        <nav>
          {sections.map((item) => <a
            className={`nav-link ${section === item.id ? "active" : ""}`}
            href={`#/${item.id}`}
            key={item.id}
            aria-current={section === item.id ? "page" : undefined}
            onClick={() => { setSection(item.id); setMobileOpen(false); }}
          ><span aria-hidden="true" className="nav-icon">{item.icon}</span>{item.label}</a>)}
        </nav>
        <div className="sidebar-bottom">
          <div className="patient-context"><span className="online-dot" />{patient ? <><strong>{patient.display_name}</strong><small>{patient.id}</small></> : <span>No patient selected</span>}</div>
          <p>Descriptive monitoring<br />Not a diagnosis</p>
        </div>
      </aside>
      <div className="main-column">
        <header className="topbar">
          <button className="menu-toggle" onClick={() => setMobileOpen(true)} aria-label="Open navigation" type="button">☰</button>
          <div className="breadcrumb"><span>Workspace</span><span aria-hidden="true">/</span><strong>{active?.label || "Not found"}</strong></div>
          <div className="account-control"><span className="avatar" aria-hidden="true">{user.display_name?.slice(0, 1)?.toUpperCase() || "U"}</span><span>{user.display_name}</span><button className="text-button" type="button" onClick={logout}>Sign out</button></div>
        </header>
        <main className="content" id="main-content" tabIndex="-1">
          {authError && <StateMessage kind="error" title="Session issue">{authError.message}</StateMessage>}
          {page}
          <footer className="app-footer"><span>TheraVoice {import.meta.env.VITE_APP_VERSION || ""}</span><span>Outputs are not medical diagnoses and do not replace professional medical judgment.</span><a href="https://github.com/omnianasa/theravoice" target="_blank" rel="noreferrer">Project documentation</a></footer>
        </main>
      </div>
    </div>
  );
}
